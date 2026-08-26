"""
download_games.py – Download top-player games from CodingGame.

Credentials are read from  rl_coding_game/.env

Two authentication methods (tried in order):
  1. CG_SESSION  – paste your browser "cgSession" cookie value  (most reliable)
  2. CG_USERNAME + CG_PASSWORD  – API login (tries several known endpoint formats)

Usage
-----
    cd rl_coding_game

    python download_games.py                     # top-5 players, 3 games each
    python download_games.py --top 10
    python download_games.py --per-player 5
    python download_games.py --game-id 123456789 # single game by known ID
    python download_games.py --no-verify         # disable SSL (corporate proxy)

Getting your session cookie (Option B in .env)
-----------------------------------------------
  1. Log in at https://www.codingame.com in your browser
  2. Open DevTools (F12) → Application → Cookies → https://www.codingame.com
  3. Copy the value of the "cgSession" cookie
  4. Paste it as  CG_SESSION=<value>  in  .env
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Core.project_paths import ensure_dir, shared_replays_dir
from Games.cellularena.engine.tools.replay_transform import codingame_to_core_raw

try:
    import requests
    import urllib3
except ImportError:
    print("Run:  pip install requests")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

BASE_URL   = "https://www.codingame.com/services"
PUZZLE_ID  = "winter-challenge-2024"
REPLAY_DIR = shared_replays_dir("cellularena")
ENV_FILE   = Path(__file__).resolve().parents[2] / ".env"

_ssl_verify = True


def _load_env() -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env


# ──────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ──────────────────────────────────────────────────────────────────────────────

def _post(endpoint: str, payload, session: requests.Session) -> Optional[dict]:
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json;charset=UTF-8"},
            timeout=20,
            verify=_ssl_verify,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.SSLError:
        print("  SSL error — re-run with --no-verify")
        return None
    except requests.HTTPError as exc:
        body = ""
        try:
            body = exc.response.text[:200]
        except Exception:
            pass
        print(f"  HTTP {exc.response.status_code} on {endpoint}: {body}")
        return None
    except requests.RequestException as exc:
        print(f"  Request error on {endpoint}: {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────────────────

def auth_with_cookie(session_cookie: str, session: requests.Session) -> Optional[int]:
    """
    Inject the cgSession browser cookie.
    Try to extract the userId from the cookie payload (it's base64-encoded JSON).
    Falls back to probing a known working endpoint.
    Returns userId (int) or 0 if it can't be determined (caller should still proceed).
    """
    session.cookies.set("cgSession", session_cookie, domain="www.codingame.com")

    # Attempt 1: decode the cookie itself (CG stores userId in the JWT/session payload)
    uid = _uid_from_cookie(session_cookie)
    if uid:
        print(f"  Cookie injected — userId={uid} (extracted from cookie)")
        return uid

    # Attempt 2: all known profile endpoints are dead as of 2025+
    # Skip probing them — just proceed with uid=0; the leaderboard works with the cookie alone.

    # Attempt 3: use userId=0; the leaderboard still works with just the cookie
    print("  Cookie injected (could not resolve userId — will use 0; this is fine)")
    return 0


def _uid_from_cookie(cookie: str) -> Optional[int]:
    """
    Try to extract the numeric userId from the cgSession cookie value.
    CodingGame session cookies are base64url-encoded JSON (sometimes gzip-compressed).
    """
    import base64, json as _json

    # Strip common prefixes like "s:" or "v:2:sess:"
    raw = cookie
    for prefix in ("s:", "v:2:sess:", "j:"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]

    # Add padding and decode
    try:
        padded = raw + "=" * (-len(raw) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        # Try plain JSON
        obj = _json.loads(decoded)
        uid = (obj.get("userId") or obj.get("user_id") or obj.get("id")
               or (obj.get("codingamer") or {}).get("userId"))
        if uid:
            return int(uid)
    except Exception:
        pass

    # Try with gzip decompression
    try:
        import zlib
        padded = raw + "=" * (-len(raw) % 4)
        compressed = base64.urlsafe_b64decode(padded)
        decoded = zlib.decompress(compressed, 16 + zlib.MAX_WBITS)
        obj = _json.loads(decoded)
        uid = obj.get("userId") or obj.get("id")
        if uid:
            return int(uid)
    except Exception:
        pass

    return None


def auth_with_credentials(
    username: str, password: str, session: requests.Session
) -> Optional[int]:
    """
    Try several known CodingGame login endpoint variants.
    Returns userId on success, None on failure.
    """
    # All variants tried in order; body MUST be a JSON array per CodingGame RPC
    print("  API login via username/password is no longer supported by CodingGame.")
    print("  Use Option B: paste your browser session cookie into .env as CG_SESSION=<value>")
    print("  Steps:")
    print("    1. Log in at https://www.codingame.com in your browser")
    print("    2. Open DevTools (F12) > Application > Cookies > https://www.codingame.com")
    print("    3. Copy the value of the 'cgSession' cookie")
    print(f"    4. Edit  {ENV_FILE}  and set  CG_SESSION=<pasted_value>")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Leaderboard + game discovery
# ──────────────────────────────────────────────────────────────────────────────

def get_my_user_id(session: requests.Session) -> int:
    """All profile endpoints are dead as of 2025+; userId is not needed."""
    return 0


def get_leaderboard(
    session: requests.Session, my_user_id: int, count: int
) -> List[Dict]:
    # Correct endpoint discovered by intercepting the live CodingGame page
    result = _post(
        "Leaderboards/getFilteredPuzzleLeaderboard",
        [PUZZLE_ID, None, "global", {"active": False, "column": "", "filter": ""}],
        session,
    )
    if result is None:
        return []
    inner = result.get("success") or result
    if isinstance(inner, list):
        return inner[:count]
    users = (inner.get("users")
             or inner.get("userSummaries")
             or inner.get("items")
             or [])
    return users[:count]


def get_tv_game(session: requests.Session) -> Optional[Tuple[int, Dict]]:
    """
    Fetch the currently broadcast TV game.
    Returns (game_id, replay_dict) or None.
    """
    result = _post(
        "Challenge/findCurrentTvGameInformation",
        [None, PUZZLE_ID],
        session,
    )
    if result is None:
        return None
    inner = result.get("success") or result
    if not isinstance(inner, dict):
        return None
    game_result = inner.get("gameResult")
    if not (game_result and game_result.get("frames")):
        return None
    game_id = (inner.get("gameId")
               or game_result.get("gameId")
               or game_result.get("id")
               or 0)
    replay = {
        "gameId":  game_id,
        "agents":  inner.get("agents", []),
        "frames":  game_result["frames"],
    }
    return int(game_id), replay


def get_player_games(
    agent_id: int, session: requests.Session, my_user_id: int
) -> List[int]:
    # API as of 2025+: takes agentId (not userId) and None as second param.
    result = _post(
        "gamesPlayersRanking/findLastBattlesByAgentId",
        [agent_id, None],
        session,
    )
    if result is None:
        return []
    # Response is a plain list; older wrapped-dict format is also handled.
    inner = result if isinstance(result, list) else (result.get("success") or result)
    items = inner if isinstance(inner, list) else []
    ids = []
    for item in items:
        gid = item.get("gameId") or item.get("id")
        if gid:
            ids.append(int(gid))
    return ids


# ──────────────────────────────────────────────────────────────────────────────
# Replay download
# ──────────────────────────────────────────────────────────────────────────────

def download_game(game_id: int, my_user_id: int, session: requests.Session) -> Optional[Dict]:
    # Passing None as userId is required — passing a real userId returns 422.
    result = _post("gameResult/findByGameId", [game_id, None], session)
    if result is None:
        return None
    return result.get("success") or result


def save_json(path: Path, data: Dict) -> Path:
    ensure_dir(REPLAY_DIR)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_core_replay(game_id: int, data: Dict, game: str = "cellularena") -> Path:
    if game == "cellularena":
        core = codingame_to_core_raw(data, source_label="download")
    else:
        # For other games, save raw CodingGame JSON under a "raw" key so
        # the game's own replay_loader can parse it later.
        core = {"format": f"{game}-raw-v1", "raw": data}
    return save_json(REPLAY_DIR / f"core_{game_id}.json", core)


def save_codingame_sample(game_id: int, data: Dict, keep_samples: int) -> Path:
    sample_path = save_json(REPLAY_DIR / f"codingame_{game_id}.json", data)
    if keep_samples < 0:
        return sample_path

    samples = sorted(
        REPLAY_DIR.glob("codingame_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in samples[keep_samples:]:
        stale.unlink(missing_ok=True)
    return sample_path


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    env = _load_env()

    parser = argparse.ArgumentParser(description="Download CodingGame replays for any puzzle")
    parser.add_argument("--url",        type=str, default="",  help="CodingGame game URL, e.g. https://www.codingame.com/contests/fall-challenge-2024")
    parser.add_argument("--top",        type=int, default=5)
    parser.add_argument("--per-player", type=int, default=3)
    parser.add_argument("--game-id",    type=int, default=None)
    parser.add_argument("--username",   type=str, default=env.get("CG_USERNAME", ""))
    parser.add_argument("--password",   type=str, default=env.get("CG_PASSWORD", ""))
    parser.add_argument("--session",    type=str, default=env.get("CG_SESSION", ""))
    parser.add_argument("--keep-samples", type=int, default=2, help="How many original CodingGame replays to keep for validation")
    parser.add_argument("--game", type=str, default="", help="Game namespace for shared replay data (default: derived from --url or --puzzle-id)")
    parser.add_argument("--puzzle-id", type=str, default="", help="CodingGame puzzle slug (e.g. 'fall-challenge-2024'). Derived from --url if omitted.")
    parser.add_argument("--replay-dir", type=str, default="", help="Override replay output directory")
    parser.add_argument("--no-verify",  action="store_true")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Seconds to wait between game downloads (default: 0.4). Increase to avoid rate-limiting.",
    )
    args = parser.parse_args()

    # Derive puzzle_id and game from --url if not set explicitly
    if args.url and not args.puzzle_id:
        from urllib.parse import urlparse as _urlparse
        parts = [p for p in _urlparse(args.url).path.split("/") if p]
        args.puzzle_id = parts[-1] if parts else ""
    if not args.game:
        args.game = args.puzzle_id.replace("-", "_") if args.puzzle_id else "cellularena"

    global PUZZLE_ID
    if args.puzzle_id:
        PUZZLE_ID = args.puzzle_id

    global REPLAY_DIR
    if args.replay_dir:
        REPLAY_DIR = Path(args.replay_dir)
    else:
        REPLAY_DIR = shared_replays_dir(args.game)
    ensure_dir(REPLAY_DIR)

    global _ssl_verify
    if args.no_verify:
        _ssl_verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("WARNING: SSL verification disabled")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; CellularenaDownloader/2.0)",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.codingame.com",
        "Referer": "https://www.codingame.com/",
    })

    # ── Authenticate (optional — TV game works without auth) ─────────────────
    my_uid: Optional[int] = 0
    cg_session = args.session.strip()

    if cg_session:
        print("Authenticating via session cookie ...")
        my_uid = auth_with_cookie(cg_session, session)

    if (my_uid is None or my_uid == 0) and args.username and args.password:
        print(f"Authenticating via credentials ('{args.username}') ...")
        my_uid = auth_with_credentials(args.username, args.password, session)

    # ── Always grab the free TV game first ──────────────────────────────────
    ensure_dir(REPLAY_DIR)
    print("Fetching broadcast TV game (no auth required) ...")
    tv = get_tv_game(session)
    if tv:
        tv_id, tv_data = tv
        core_path = save_core_replay(tv_id, tv_data, args.game)
        sample_path = save_codingame_sample(tv_id, tv_data, args.keep_samples)
        turns = len(tv_data.get("frames", [])) // 2
        agents_info = tv_data.get("agents", [])
        agents = " vs ".join(a.get("name", a.get("pseudo", "?")) for a in agents_info[:2])
        if not agents:
            agents = "(no agent names)"
        print(f"  [{tv_id}] {turns} turns  {agents}  -> {core_path.name} (sample: {sample_path.name})")
        downloaded = 1
    else:
        print("  No TV game available right now")
        downloaded = 0

    if not (cg_session or args.username):
        # No auth — can only download the TV game
        print(f"\nDone (no auth): {downloaded} game(s) in {REPLAY_DIR}")
        return

    # ── Single game by ID ────────────────────────────────────────────────────
    if args.game_id:
        print(f"Downloading game {args.game_id} ...")
        data = download_game(args.game_id, my_uid or 0, session)
        if data:
            core_path = save_core_replay(args.game_id, data, args.game)
            sample_path = save_codingame_sample(args.game_id, data, args.keep_samples)
            turns  = len(data.get("frames", [])) - 1
            agents = " vs ".join(a.get("name", "?") for a in data.get("agents", [])[:2])
            print(f"  Saved {turns} turns  [{agents}]  -> {core_path.name} (sample: {sample_path.name})")
        else:
            print("  Failed.")
        return

    # ── Top-N leaderboard → recent games ─────────────────────────────────────
    print(f"\nFetching leaderboard (top {args.top}) ...")
    users = get_leaderboard(session, my_uid or 0, args.top)

    if not users:
        print("  Could not fetch leaderboard — leaderboard may require login.")
        print(f"  Set CG_SESSION in {ENV_FILE} and re-run.")
        print(f"\nDone: {downloaded} game(s) saved to {REPLAY_DIR}")
        return

    print(f"  {len(users)} players found")
    skipped = failed = 0

    for user in users:
        # agentId is the bot submission ID used by the battles endpoint.
        # userId lives inside the nested 'codingamer' object.
        agent_id = user.get("agentId") or 0
        codingamer = user.get("codingamer") or {}
        uid  = codingamer.get("userId") or user.get("userId") or user.get("id") or 0
        name = user.get("pseudo") or codingamer.get("pseudo") or str(uid)
        rank = user.get("rank") or "?"
        print(f"\n  #{rank}  {name}  (agentId={agent_id})")

        game_ids = get_player_games(agent_id, session, my_uid or 0)
        if not game_ids:
            print("    No recent games found")
            continue

        for gid in game_ids[: args.per_player]:
            dest = REPLAY_DIR / f"core_{gid}.json"
            if dest.exists():
                print(f"    [{gid}] already saved")
                skipped += 1
                continue
            data = download_game(gid, my_uid, session)
            if data:
                save_core_replay(gid, data, args.game)
                save_codingame_sample(gid, data, args.keep_samples)
                turns  = len(data.get("frames", [])) - 1
                agents = " vs ".join(a.get("name", "?") for a in data.get("agents", [])[:2])
                print(f"    [{gid}] {turns} turns  {agents}")
                downloaded += 1
            else:
                print(f"    [{gid}] failed")
                failed += 1
            if args.delay > 0:
                time.sleep(args.delay)

    print(f"\nDone: {downloaded} downloaded, {skipped} already existed, {failed} failed")
    print(f"Replays in: {REPLAY_DIR}")


if __name__ == "__main__":
    main()
