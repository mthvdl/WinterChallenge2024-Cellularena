"""
viewer_server.py - Serve Cellularena viewer UI + in-memory replay conversion API.

Usage:
    python viewer_server.py --port 8000

Then open:
    http://localhost:8000/Games/cellularena/deploy/viewer/view/index.html
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Games.cellularena.engine.tools.replay_transform import (
    _infer_initial_storage,
    add_display_data,
    codingame_to_core_raw,
    load_replay_from_dict,
)

def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _to_viewer_in_memory(raw: Dict[str, Any]) -> Dict[str, Any]:
    # Keep output ephemeral: convert in memory and return only HTTP response body.
    if raw.get("format") == "cellularena-core-raw-v1":
        core = dict(raw)
        reference_turn_events = None
        if not core.get("initialStorage"):
            game_id = core.get("gameId")
            sample_path = PROJECT_ROOT / "Games" / "cellularena" / "experiments" / "shared" / "replays" / f"codingame_{game_id}.json"
            if sample_path.exists():
                sample = json.loads(sample_path.read_text(encoding="utf-8"))
                replay = load_replay_from_dict(sample if "success" in sample else {"success": sample})
                inferred = _infer_initial_storage(core.get("globalData", ""), replay)
                if inferred:
                    core["initialStorage"] = inferred
                reference_turn_events = {
                    int(t.turn): t.frame_data.events
                    for t in replay.turns
                }

        return add_display_data(core, reference_turn_events=reference_turn_events)

    wrapped = raw.get("success") if isinstance(raw.get("success"), dict) else raw

    if wrapped.get("format") == "cellularena-core-raw-v1":
        return add_display_data(wrapped)

    core = codingame_to_core_raw(raw)
    return add_display_data(core)


class ViewerRequestHandler(BaseHTTPRequestHandler):
    server_version = "CellularenaViewerServer/1.0"
    _replays_dir: Optional[Path] = None

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/convert-replay":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid Content-Length"})
            return

        if length <= 0:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Missing request body"})
            return

        try:
            raw_body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw_body)
        except Exception as exc:  # noqa: BLE001
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON body: {exc}"})
            return

        replay = payload.get("replay", payload)
        if not isinstance(replay, dict):
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Replay payload must be a JSON object"})
            return

        try:
            viewer_replay = _to_viewer_in_memory(replay)
        except Exception as exc:  # noqa: BLE001
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        response_payload = {
            "ok": True,
            "viewerReplay": viewer_replay,
            "meta": {
                "ephemeral": True,
                "stored": False,
            },
        }

        body = json.dumps(response_payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            _json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if parsed.path == "/api/replays":
            self._handle_list_replays()
            return

        if parsed.path.startswith("/api/replay-data/"):
            name = unquote(parsed.path[len("/api/replay-data/"):])
            self._handle_replay_data(name)
            return

        rel = unquote(parsed.path)
        if rel in ("", "/"):
            rel = "/view/index.html"

        base_dir = PROJECT_ROOT / "Games" if rel.startswith("/Games/") else ROOT_DIR
        relative_path = rel[len("/Games/"):] if rel.startswith("/Games/") else rel.lstrip("/")
        file_path = (base_dir / relative_path).resolve()
        if base_dir not in file_path.parents and file_path != base_dir:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        ctype, _ = mimetypes.guess_type(file_path.name)
        if ctype is None:
            ctype = "application/octet-stream"

        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_list_replays(self) -> None:
        if self._replays_dir is None or not self._replays_dir.is_dir():
            _json_response(self, HTTPStatus.OK, {"replays": [], "error": "No replays-dir configured"})
            return
        entries = []
        for path in sorted(self._replays_dir.glob("*.viewer.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                turns = max(0, len(data.get("frames", [])) - 1)
            except Exception:  # noqa: BLE001
                turns = 0
            entries.append({"name": path.name, "mtime": path.stat().st_mtime, "turns": turns})
        _json_response(self, HTTPStatus.OK, {"replays": entries})

    def _handle_replay_data(self, name: str) -> None:
        if self._replays_dir is None:
            self.send_error(HTTPStatus.NOT_FOUND, "No replays-dir configured")
            return
        safe_name = Path(name).name  # strip any path components
        if not safe_name.endswith(".viewer.json"):
            self.send_error(HTTPStatus.FORBIDDEN, "Only .viewer.json files served here")
            return
        path = self._replays_dir / safe_name
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Replay not found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve viewer UI with in-memory replay conversion API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument(
        "--replays-dir",
        default=None,
        help="Directory to scan for *.viewer.json checkpoint replays (enables /api/replays).",
    )
    args = parser.parse_args()

    if args.replays_dir:
        ViewerRequestHandler._replays_dir = Path(args.replays_dir).resolve()
        print(f"Replays dir: {ViewerRequestHandler._replays_dir}")

    server = ThreadingHTTPServer((args.host, args.port), ViewerRequestHandler)
    print(f"Serving on http://{args.host}:{args.port}")
    print("UI:       /view/index.html")
    print("API:      POST /api/convert-replay")
    print("Replays:  GET  /api/replays")
    print("Health:   GET  /api/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
