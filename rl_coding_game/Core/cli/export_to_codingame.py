#!/usr/bin/env python3
"""Export a trained Rainbow/DQN bot to a CodinGame-ready Python file.

CodinGame Python constraints (verified as of 2024)
---------------------------------------------------
- Language  : Python 3
- Libraries : numpy, scipy (plus the standard library)
- File limit: 100 000 **characters** (total source)
- Time limit: 1 000 ms first turn / 50 ms subsequent turns

The generated file:
- Uses only ``import numpy`` (no PyTorch at runtime)
- Decodes gzip-compressed quantised weights from an embedded base64 blob
- Runs the QR-DQN / dueling / Rainbow forward pass in pure numpy
- Exposes ``select_action(obs_flat) -> np.ndarray`` for the game loop

Size budget (rough guide at fp16 + gzip)
-----------------------------------------
+-------------+----------+--------+-----------+------------------+
| hidden_dim  | n_quant  | params | blob (KB) | total chars      |
+-------------+----------+--------+-----------+------------------+
| 64          | 16       |  ~30 k |  ~10 KB   |  ~15 000   ✓    |
| 128         | 32       | ~110 k |  ~40 KB   |  ~55 000   ✓    |
| 256         | 64       | ~450 k | ~170 KB   | ~230 000   ✗    |
+-------------+----------+--------+-----------+------------------+
Use ``--quantize int8`` to roughly halve the blob size if needed.

Usage
-----
1. Write a small "loader script" that builds and returns a trained network::

    # my_loader.py
    from Games.cellularena.engine.env import CellularenaEnv
    from Games.cellularena.ray.dqn import DQNBot

    env = CellularenaEnv()
    agent = list(env.possible_agents)[0]
    bot = DQNBot(env.observation_space(agent), env.action_space(agent)).build()
    bot.load("runs/my_run/checkpoint.pt")
    network = bot.network          # ← the exporter reads this variable

2. Run the exporter::

    python -m Core.cli.export_to_codingame \\
        --bot-script my_loader.py \\
        --output cg_bot.py \\
        [--quantize fp16]          # default; fp16 ≈ 2× smaller than fp32
        [--quantize int8]          # 4× smaller, slight precision loss
        [--game-loop game_loop.py] # Python file appended verbatim as loop

3. Copy ``cg_bot.py`` to the CodinGame IDE.

The network must implement ``BaseNetwork.export_ops()``; see
``rl/base_network.py`` for the format.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Op-tree utilities
# ---------------------------------------------------------------------------

def _iter_linear_ops(ops: list[dict]):
    """Yield every ``"linear"`` op in depth-first order (including in dueling)."""
    for op in ops:
        if op["op"] == "linear":
            yield op
        elif op["op"] == "dueling":
            yield from _iter_linear_ops(op["v_layers"])
            yield from _iter_linear_ops(op["a_layers"])


def _strip_arrays(ops: list[dict]) -> list[dict]:
    """Return a deep copy of *ops* with numpy arrays removed."""
    result = []
    for op in ops:
        o = {k: v for k, v in op.items() if k not in ("W", "b")}
        if op["op"] == "dueling":
            o["v_layers"] = _strip_arrays(op["v_layers"])
            o["a_layers"] = _strip_arrays(op["a_layers"])
        result.append(o)
    return result


def _validate_ops(ops: list[dict]) -> None:
    """Basic sanity checks on the op list."""
    ids = [op["id"] for op in _iter_linear_ops(ops)]
    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate layer IDs found in export_ops() output. "
            "Each linear op must have a unique integer 'id'."
        )
    for op in _iter_linear_ops(ops):
        W = np.asarray(op["W"])
        b = np.asarray(op["b"])
        if W.ndim != 2:
            raise ValueError(f"Layer id={op['id']}: W must be 2-D, got shape {W.shape}")
        if b.ndim != 1:
            raise ValueError(f"Layer id={op['id']}: b must be 1-D, got shape {b.shape}")
        if W.shape[0] != b.shape[0]:
            raise ValueError(
                f"Layer id={op['id']}: W.shape[0]={W.shape[0]} != b.shape[0]={b.shape[0]}"
            )


# ---------------------------------------------------------------------------
# Quantisation
# ---------------------------------------------------------------------------

def _quantize_fp16(W: np.ndarray) -> tuple[np.ndarray, None]:
    return W.astype(np.float16), None


def _quantize_int8(W: np.ndarray) -> tuple[np.ndarray, float]:
    """Per-tensor absmax int8 quantisation.  Returns (int8_array, scale)."""
    amax = float(np.abs(W).max())
    scale = amax / 127.0 if amax > 0 else 1.0
    scale = max(scale, 1e-9)
    q = np.clip(np.round(W / scale), -128, 127).astype(np.int8)
    return q, scale


# ---------------------------------------------------------------------------
# Pack: ops → gzip+npz+base64 blob
# ---------------------------------------------------------------------------

def pack(ops: list[dict], quantize: str = "fp16") -> tuple[str, bool]:
    """Serialise *ops* to a gzip-compressed npz blob encoded as base64.

    Parameters
    ----------
    ops:
        List of op dicts as returned by ``BaseNetwork.export_ops()``.
    quantize:
        ``"fp16"`` (default) or ``"int8"``.

    Returns
    -------
    blob_b64:
        ASCII base64 string ready to embed in the generated Python file.
    is_gzipped:
        ``True`` if an extra gzip pass was applied on top of the npz.
    """
    _validate_ops(ops)

    arrays: dict[str, np.ndarray] = {}
    raw_bytes = 0

    for op in _iter_linear_ops(ops):
        i = op["id"]
        W = np.asarray(op["W"], dtype=np.float32)
        b = np.asarray(op["b"], dtype=np.float32)
        raw_bytes += W.nbytes + b.nbytes

        if quantize == "fp16":
            arrays["W" + str(i)] = W.astype(np.float16)
            arrays["b" + str(i)] = b.astype(np.float16)
        elif quantize == "int8":
            qW, sW = _quantize_int8(W)
            arrays["W" + str(i)] = qW
            arrays["s" + str(i)] = np.array([sW], dtype=np.float32)
            # biases are small – keep fp16 for accuracy
            arrays["b" + str(i)] = b.astype(np.float16)
        else:
            raise ValueError(f"Unknown --quantize value: {quantize!r}")

    arch_clean = _strip_arrays(ops)
    arch_bytes = json.dumps(arch_clean, separators=(",", ":")).encode()
    arrays["arch"] = np.frombuffer(arch_bytes, dtype=np.uint8)

    # Uncompressed npz + gzip is usually smaller than npz_compressed alone
    buf = io.BytesIO()
    np.savez(buf, **arrays)
    npz_raw = buf.getvalue()

    gz = gzip.compress(npz_raw, compresslevel=9)

    if len(gz) < len(npz_raw):
        final, is_gz = gz, True
    else:
        final, is_gz = npz_raw, False

    blob = base64.b64encode(final).decode("ascii")

    q_bytes = sum(a.nbytes for k, a in arrays.items() if k != "arch")
    print(f"  Raw float32 weights : {raw_bytes / 1024:7.1f} KB")
    print(f"  After {quantize:<4} quantise : {q_bytes / 1024:7.1f} KB")
    print(f"  NPZ (uncompressed)  : {len(npz_raw) / 1024:7.1f} KB")
    print(f"  Final blob          : {len(final) / 1024:7.1f} KB"
          f"  ({'gzip+npz' if is_gz else 'npz only'})")
    print(f"  Base64 chars        : {len(blob):>9,}")

    return blob, is_gz


# ---------------------------------------------------------------------------
# Inference-engine template
# ---------------------------------------------------------------------------

# This is the pure-numpy inference engine that will be embedded verbatim in
# the generated bot file.  __BLOB__ and __GZIPPED__ are replaced at generation
# time; all other identifiers are final Python.

_ENGINE_TEMPLATE = '''\
import sys,io,base64,gzip
import numpy as np

# --- weights blob (generated by export_to_codingame.py) ---
_B="__BLOB__"
_G=__GZIPPED__

def _load_weights():
    raw=base64.b64decode(_B)
    if _G:raw=gzip.decompress(raw)
    npz=np.load(io.BytesIO(raw),allow_pickle=False)
    import json
    arch=json.loads(bytes(npz["arch"]).decode())
    return arch,dict(npz)

_ARCH,_WW=_load_weights()

# --- activation helper ---
def _act(x,name):
    if name=="relu":return np.maximum(0.,x)
    if name=="tanh":return np.tanh(x)
    if name=="lrelu":return np.where(x>=0,x,0.01*x)
    return x  # None / identity

# --- linear layer (handles fp16 and int8 with per-tensor scale) ---
def _lin(x,layer_id):
    k=str(layer_id)
    W=_WW["W"+k].astype(np.float32)
    b=_WW["b"+k].astype(np.float32)
    sk="s"+k
    if sk in _WW:  # int8: dequantise weights (biases already fp16)
        W=W*float(_WW[sk][0])
    return x@W.T+b

# --- run a sequence of linear ops ---
def _seq(x,layers):
    for l in layers:
        x=_act(_lin(x,l["id"]),l.get("act"))
    return x

# --- main forward pass ---
def forward(obs):
    """obs: 1-D float array (flattened observation). Returns Q-quantile tensor."""
    x=np.asarray(obs,dtype=np.float32).ravel()
    for op in _ARCH:
        t=op["op"]
        if t=="linear":
            x=_act(_lin(x,op["id"]),op.get("act"))
        elif t=="dueling":
            nq=op["n_quantiles"]
            sh=op["action_shape"]  # list[int]
            v=_seq(x,op["v_layers"]).reshape(nq)           # (nq,)
            a=_seq(x,op["a_layers"])
            if len(sh)==1:
                # Discrete(n)
                a=a.reshape(sh[0],nq)                       # (n,nq)
                x=v+a-a.mean(0,keepdims=True)               # (n,nq)
            else:
                # MultiDiscrete([n0,n1,...]) – independent per-dimension head
                nd=len(sh);mx=max(sh)
                a=a.reshape(nd,mx,nq)                       # (nd,mx,nq)
                x=v+a-a.mean(1,keepdims=True)               # (nd,mx,nq)
    return x  # (*action_shape, nq)

# --- greedy action selection ---
def select_action(obs):
    """obs: 1-D float array. Returns int array matching action_space shape."""
    q=forward(obs).mean(-1)  # (*action_shape) – expected Q over quantiles
    last=[op for op in _ARCH if op["op"]=="dueling"][-1]
    sh=last["action_shape"]
    if len(sh)==1:
        return np.array([int(q.argmax())])
    return np.array([int(q[d].argmax()) for d in range(len(sh))])

'''

_GAME_LOOP_STUB = '''\
# =============================================================================
# GAME LOOP  –  replace this section with your actual game I/O
# =============================================================================
# select_action(obs_flat) returns a numpy int array matching your action_space.
#
# Quick reference:
#   obs_flat = np.array([...], dtype=np.float32)  # your encoded observation
#   action   = select_action(obs_flat)             # e.g. array([2, 0, 3])
#
# import sys
# while True:
#     # 1. Parse stdin into a flat float32 numpy array
#     obs_flat = parse_observation()
#     # 2. Pick action
#     action = select_action(obs_flat)
#     # 3. Encode and print to stdout
#     print(encode_action(action))
#     sys.stdout.flush()
'''


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

def generate(blob: str, is_gzipped: bool, game_loop_path: str | None = None) -> str:
    """Render the final bot Python source."""
    header = (
        "# CodinGame bot – generated by export_to_codingame.py\n"
        "# Pure numpy inference – no PyTorch required at runtime.\n\n"
    )
    engine = _ENGINE_TEMPLATE.replace("__BLOB__", blob).replace("__GZIPPED__", str(is_gzipped))
    if game_loop_path:
        loop = Path(game_loop_path).read_text(encoding="utf-8")
    else:
        loop = _GAME_LOOP_STUB
    return header + engine + loop


# ---------------------------------------------------------------------------
# Verification helper
# ---------------------------------------------------------------------------

def verify(ops: list[dict], blob: str, is_gzipped: bool, n_samples: int = 8) -> None:
    """Check that the numpy engine produces the same argmax as the op-list."""
    import warnings

    # Determine input size from first linear op
    first_op = next(_iter_linear_ops(ops))
    in_dim = np.asarray(first_op["W"]).shape[1]

    # Build the generated module in-memory
    code = generate(blob, is_gzipped)
    ns: dict[str, Any] = {}
    exec(compile(code, "<generated>", "exec"), ns)  # noqa: S102

    rng = np.random.default_rng(0)
    mismatches = 0
    for _ in range(n_samples):
        obs = rng.standard_normal(in_dim).astype(np.float32)

        # Reference: run ops with float32 precision (no quantisation error)
        x = obs.copy()
        for op in ops:
            t = op["op"]
            if t == "linear":
                W = np.asarray(op["W"], dtype=np.float32)
                b = np.asarray(op["b"], dtype=np.float32)
                act_name = op.get("act")
                x = x @ W.T + b
                if act_name == "relu":
                    x = np.maximum(0.0, x)
                elif act_name == "tanh":
                    x = np.tanh(x)
                elif act_name == "lrelu":
                    x = np.where(x >= 0, x, 0.01 * x)
            elif t == "dueling":
                nq = op["n_quantiles"]
                sh = op["action_shape"]
                # run v/a streams using the same _run_layers logic
                def run_stream(x0, layers):
                    for l in layers:
                        W = np.asarray(l["W"], dtype=np.float32)
                        b = np.asarray(l["b"], dtype=np.float32)
                        x0 = x0 @ W.T + b
                        n = l.get("act")
                        if n == "relu":
                            x0 = np.maximum(0.0, x0)
                        elif n == "tanh":
                            x0 = np.tanh(x0)
                        elif n == "lrelu":
                            x0 = np.where(x0 >= 0, x0, 0.01 * x0)
                    return x0
                v = run_stream(x.copy(), op["v_layers"]).reshape(nq)
                a = run_stream(x.copy(), op["a_layers"])
                if len(sh) == 1:
                    a = a.reshape(sh[0], nq)
                    x = v + a - a.mean(0, keepdims=True)
                else:
                    nd, mx = len(sh), max(sh)
                    a = a.reshape(nd, mx, nq)
                    x = v + a - a.mean(1, keepdims=True)
        ref_q = x.mean(-1)
        last_dueling = [op for op in ops if op["op"] == "dueling"][-1]
        sh = last_dueling["action_shape"]
        if len(sh) == 1:
            ref_action = np.array([int(ref_q.argmax())])
        else:
            ref_action = np.array([int(ref_q[d].argmax()) for d in range(len(sh))])

        gen_action = ns["select_action"](obs)
        if not np.array_equal(ref_action, gen_action):
            mismatches += 1
            warnings.warn(
                f"Argmax mismatch: ref={ref_action} gen={gen_action}  "
                "(likely due to quantisation error near Q-value ties)",
                stacklevel=2,
            )

    if mismatches == 0:
        print(f"  Verification: all {n_samples} samples match ✓")
    else:
        print(f"  Verification: {mismatches}/{n_samples} argmax mismatches "
              "(quantisation noise; check if acceptable for your use case)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--bot-script",
        required=True,
        metavar="PATH",
        help=(
            "Path to a Python script that, when exec'd, defines a variable "
            "``network`` holding a trained BaseNetwork in eval mode.  "
            "Example:  network = bot.network  (after bot.load('ckpt.pt'))"
        ),
    )
    p.add_argument(
        "--output",
        default="cg_bot.py",
        metavar="PATH",
        help="Output Python file (default: cg_bot.py)",
    )
    p.add_argument(
        "--quantize",
        choices=["fp16", "int8"],
        default="fp16",
        help=(
            "Weight quantisation: fp16 (default, halves fp32 size) or "
            "int8 (quarters size, slight accuracy loss)."
        ),
    )
    p.add_argument(
        "--game-loop",
        default=None,
        metavar="PATH",
        help="Python file appended verbatim as the game I/O loop.",
    )
    p.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip the argmax verification step.",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    # ── Load the network via the user-supplied loader script ──────────────────
    print(f"Running loader script: {args.bot_script}")
    loader_ns: dict[str, Any] = {}
    loader_code = Path(args.bot_script).read_text(encoding="utf-8")
    exec(compile(loader_code, args.bot_script, "exec"), loader_ns)  # noqa: S102

    if "network" not in loader_ns:
        sys.exit(
            "ERROR: The loader script must define a variable named 'network' "
            "(a trained BaseNetwork instance).  Example:\n"
            "  bot.load('checkpoint.pt')\n"
            "  network = bot.network"
        )

    network = loader_ns["network"]
    network.eval()

    # ── Extract inference ops ─────────────────────────────────────────────────
    print("Extracting inference ops from network.export_ops() ...")
    ops = network.export_ops()
    n_layers = sum(1 for _ in _iter_linear_ops(ops))
    print(f"  Found {n_layers} linear layer(s) in the inference graph.")

    # ── Pack weights ──────────────────────────────────────────────────────────
    print(f"\nPacking weights (--quantize {args.quantize}) ...")
    blob, is_gz = pack(ops, args.quantize)

    # ── Generate bot file ─────────────────────────────────────────────────────
    print("\nGenerating bot file ...")
    code = generate(blob, is_gz, args.game_loop)
    actual_chars = len(code)
    print(f"  Total characters: {actual_chars:,}")

    CG_LIMIT = 100_000
    if actual_chars > CG_LIMIT:
        print(
            f"\nERROR: Generated file exceeds CodinGame's {CG_LIMIT:,}-char limit "
            f"({actual_chars:,} chars).\n"
            "  Suggestions:\n"
            "  • Use --quantize int8\n"
            "  • Reduce network hidden_dim\n"
            "  • Reduce n_quantiles (e.g. 16 or 8)\n"
            "  • Reduce the number of layers"
        )
        sys.exit(1)
    elif actual_chars > 80_000:
        print(
            f"  WARNING: {actual_chars:,}/{CG_LIMIT:,} chars used.  "
            "Make sure your game loop fits in the remaining budget."
        )
    else:
        pct = actual_chars / CG_LIMIT * 100
        print(f"  {actual_chars:,}/{CG_LIMIT:,} chars  ({pct:.1f}% of limit)  ✓")

    # ── Optional verification ─────────────────────────────────────────────────
    if not args.no_verify:
        print("\nVerifying numpy engine against reference ops ...")
        verify(ops, blob, is_gz)

    # ── Write output ──────────────────────────────────────────────────────────
    out = Path(args.output)
    out.write_text(code, encoding="utf-8")
    print(f"\nBot written to: {out}")


if __name__ == "__main__":
    main()
