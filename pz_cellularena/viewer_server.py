"""
viewer_server.py - Serve Cellularena viewer UI + in-memory replay conversion API.

Usage:
    python viewer_server.py --port 8000

Then open:
    http://localhost:8000/viewer/view/index.html
"""
from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote, urlparse

from replay_transform import add_display_data, codingame_to_core_raw, _infer_initial_storage, load_replay_from_dict

ROOT_DIR = Path(__file__).resolve().parent


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
            sample_path = ROOT_DIR / "replays" / f"codingame_{game_id}.json"
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

        rel = unquote(parsed.path)
        if rel in ("", "/"):
            rel = "/viewer/view/index.html"

        file_path = (ROOT_DIR / rel.lstrip("/")).resolve()
        if ROOT_DIR not in file_path.parents and file_path != ROOT_DIR:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve viewer UI with in-memory replay conversion API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ViewerRequestHandler)
    print(f"Serving on http://{args.host}:{args.port}")
    print("UI:       /viewer/view/index.html")
    print("API:      POST /api/convert-replay")
    print("Health:   GET  /api/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
