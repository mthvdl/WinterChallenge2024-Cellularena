"""
download_rules.py – Download the game statement (rules) for a CodingGame puzzle.

Usage
-----
    cd rl_coding_game

    # From a full CodingGame URL:
    python download_rules.py --url https://www.codingame.com/contests/fall-challenge-2024

    # From a puzzle slug directly:
    python download_rules.py --puzzle-id fall-challenge-2024

    # Specify output directory (default: data/games/<game>/):
    python download_rules.py --puzzle-id fall-challenge-2024 --game blockout

The script saves:
  - data/games/<game>/rules.html  — raw HTML statement (best for reading)
  - data/games/<game>/rules.txt   — plain-text extraction (best for LLM context)

Authentication (optional — public statement endpoint works without auth):
  Set CG_SESSION in .env for auth-gated statements.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from project_paths import ensure_dir, shared_game_root

try:
    import requests
    import urllib3
except ImportError:
    print("Run:  pip install requests")
    sys.exit(1)

BASE_URL = "https://www.codingame.com/services"
ENV_FILE = Path(__file__).parent / ".env"
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
        print(f"  HTTP {exc.response.status_code} on {endpoint}: {exc.response.text[:200]}")
        return None
    except requests.RequestException as exc:
        print(f"  Request error on {endpoint}: {exc}")
        return None


def _html_to_text(html: str) -> str:
    """Very lightweight HTML → plain text (no external deps)."""
    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace common block tags with newlines
    html = re.sub(r"<(br|p|div|li|h[1-6]|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</?(ul|ol|table|thead|tbody)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode common HTML entities
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                          ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        html = html.replace(entity, char)
    # Collapse whitespace
    lines = [l.rstrip() for l in html.splitlines()]
    # Remove runs of blank lines
    result: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    return "\n".join(result).strip()


def slug_from_url(url: str) -> str:
    """Extract the puzzle slug from a CodingGame URL."""
    parsed = urlparse(url)
    # Last non-empty segment of the path
    parts = [p for p in parsed.path.split("/") if p]
    return parts[-1] if parts else url


def fetch_statement(puzzle_id: str, session: requests.Session) -> Optional[str]:
    """Try multiple CodingGame API endpoints to get the puzzle statement HTML."""

    # Endpoint 1: generateSessionFromPuzzlePrettyId (works for most multi puzzles)
    result = _post(
        "Puzzle/generateSessionFromPuzzlePrettyId",
        [None, puzzle_id, False],
        session,
    )
    if result:
        inner = result.get("success") or result
        if isinstance(inner, dict):
            statement = (
                inner.get("statement")
                or (inner.get("puzzle") or {}).get("statement")
                or (inner.get("currentQuestion") or {}).get("statement")
            )
            if statement:
                return str(statement)

    # Endpoint 2: findAllMinimalProgress for contest puzzles
    result2 = _post(
        "Contest/findContestByPublicId",
        [puzzle_id],
        session,
    )
    if result2:
        inner2 = result2.get("success") or result2
        if isinstance(inner2, dict):
            statement = inner2.get("description") or inner2.get("statement")
            if statement:
                return str(statement)

    return None


def main() -> None:
    env = _load_env()

    parser = argparse.ArgumentParser(
        description="Download a CodingGame puzzle statement (rules)"
    )
    parser.add_argument(
        "--url", type=str, default="",
        help="Full CodingGame URL, e.g. https://www.codingame.com/contests/fall-challenge-2024"
    )
    parser.add_argument(
        "--puzzle-id", type=str, default="",
        help="CodingGame puzzle slug, e.g. 'fall-challenge-2024'"
    )
    parser.add_argument(
        "--game", type=str, default="",
        help="Local game name (used for output dir). Defaults to puzzle-id."
    )
    parser.add_argument("--session", type=str, default=env.get("CG_SESSION", ""))
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()

    global _ssl_verify
    if args.no_verify:
        _ssl_verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Resolve puzzle ID
    puzzle_id = args.puzzle_id
    if not puzzle_id and args.url:
        puzzle_id = slug_from_url(args.url)
    if not puzzle_id:
        print("ERROR: provide --url or --puzzle-id")
        sys.exit(1)

    game = args.game or puzzle_id
    out_dir = ensure_dir(shared_game_root(game))

    print(f"Puzzle ID : {puzzle_id}")
    print(f"Output dir: {out_dir}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.codingame.com",
        "Referer": "https://www.codingame.com/",
    })
    if args.session:
        session.cookies.set("cgSession", args.session, domain="www.codingame.com")

    print("Fetching puzzle statement ...")
    html = fetch_statement(puzzle_id, session)

    if not html:
        print("  Could not retrieve statement via API.")
        print("  The game rules page is at:")
        print(f"    https://www.codingame.com/contests/{puzzle_id}")
        print("  Open it in a browser and copy the statement manually.")
        sys.exit(1)

    html_path = out_dir / "rules.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  Saved HTML: {html_path}")

    txt_path = out_dir / "rules.txt"
    txt_path.write_text(_html_to_text(html), encoding="utf-8")
    print(f"  Saved text: {txt_path}")


if __name__ == "__main__":
    main()
