"""
download_rules.py – Download the game statement (rules) for a CodingGame puzzle.

Usage
-----
    cd rl_coding_game

    # From a full CodingGame URL:
    conda run -n cellularena python download_rules.py --url https://www.codingame.com/contests/fall-challenge-2024

    # From a puzzle slug directly:
    conda run -n cellularena python download_rules.py --puzzle-id fall-challenge-2024

    # Specify output directory (default: Games/<game>/):
    conda run -n cellularena python download_rules.py --puzzle-id fall-challenge-2024 --game blockout

The script saves:
    - Games/<game>/rules.md         — Markdown statement (best for implementation notes)
    - Games/<game>/rules.html       — raw HTML statement (for debugging/traceability)
    - Games/<game>/rules.txt        — plain-text extraction (best for LLM context)

Authentication (optional — public statement endpoint works without auth):
    Set CG_SESSION in env.secret.sh/.env for auth-gated statements.
    Optionally set CG_USER_ID to force league-specific statement retrieval.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from html import unescape
from pathlib import Path
from typing import Dict, Optional, Union
from urllib.parse import urlparse

from Core.project_paths import ROOT, ensure_dir, shared_game_root

try:
    import requests
    import urllib3
except ImportError:
    print("Run:  pip install requests")
    sys.exit(1)

BASE_URL = "https://www.codingame.com/services"
IDE_URL = "https://www.codingame.com/ide/puzzle/{puzzle_id}"
ENV_FILE = Path(__file__).parent / ".env"
ENV_SECRET_FILE = ROOT / "env.secret.sh"
WORKSPACE_SECRET_FILE = ROOT.parent / "env.secret.sh"
_ssl_verify: Union[bool, str] = True
_ssl_fallback_used = False


def _resolve_verify_setting(no_verify: bool, env: Dict[str, str]) -> Union[bool, str]:
    """Resolve TLS verify setting with env overrides and certifi fallback."""
    if no_verify:
        return False

    for key in ("CG_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        path = env.get(key) or os.environ.get(key)
        if path and Path(path).exists():
            return path

    try:
        import certifi  # type: ignore

        ca_path = certifi.where()
        if ca_path and Path(ca_path).exists():
            return ca_path
    except Exception:
        pass

    return True


def _load_kv_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip().replace("\r", "")
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        if "=" not in line:
            continue

        key, _, val = line.partition("=")
        cleaned = val.strip().strip('"').strip("'")
        values[key.strip()] = cleaned
    return values


def _load_env() -> Dict[str, str]:
    env: Dict[str, str] = {}

    # Precedence: .env (lowest) -> env.secret.sh -> workspace env.secret.sh
    # Explicit process env still overrides via argparse defaults below.
    env.update(_load_kv_file(ENV_FILE))
    env.update(_load_kv_file(ENV_SECRET_FILE))
    env.update(_load_kv_file(WORKSPACE_SECRET_FILE))
    return env


def _post(endpoint: str, payload, session: requests.Session) -> Optional[dict]:
    global _ssl_verify, _ssl_fallback_used
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
        if _ssl_verify is not False:
            if not _ssl_fallback_used:
                print("  SSL error with certificate verification; switching to --no-verify fallback for this run")
                _ssl_fallback_used = True
            _ssl_verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                r = session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json;charset=UTF-8"},
                    timeout=20,
                    verify=False,
                )
                r.raise_for_status()
                return r.json()
            except requests.HTTPError as exc:
                print(f"  HTTP {exc.response.status_code} on {endpoint}: {exc.response.text[:200]}")
                return None
            except requests.RequestException as exc:
                print(f"  Request error on {endpoint}: {exc}")
                return None
        print("  SSL error — re-run with --no-verify")
        return None
    except requests.HTTPError as exc:
        print(f"  HTTP {exc.response.status_code} on {endpoint}: {exc.response.text[:200]}")
        return None
    except requests.RequestException as exc:
        print(f"  Request error on {endpoint}: {exc}")
        return None


def _get(url: str, session: requests.Session) -> Optional[str]:
    global _ssl_verify, _ssl_fallback_used
    try:
        r = session.get(url, timeout=20, verify=_ssl_verify)
        r.raise_for_status()
        return r.text
    except requests.exceptions.SSLError:
        if _ssl_verify is not False:
            if not _ssl_fallback_used:
                print("  SSL error with certificate verification; switching to --no-verify fallback for this run")
                _ssl_fallback_used = True
            _ssl_verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                r = session.get(url, timeout=20, verify=False)
                r.raise_for_status()
                return r.text
            except requests.RequestException as exc:
                print(f"  Request error on GET {url}: {exc}")
                return None
        return None
    except requests.RequestException as exc:
        print(f"  Request error on GET {url}: {exc}")
        return None


def _html_to_text(html: str) -> str:
    """Very lightweight HTML -> plain text (no external deps)."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r"<li[^>]*>", "\n- ", html, flags=re.IGNORECASE)
    html = re.sub(r"<(br|p|div|li|h[1-6]|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</?(ul|ol|table|thead|tbody)[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "", html)
    html = unescape(html).replace("\xa0", " ")

    lines = [l.rstrip() for l in html.splitlines()]
    result: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    return "\n".join(result).strip()


def _clean_inline(fragment: str) -> str:
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = unescape(fragment).replace("\xa0", " ")
    return re.sub(r"\s+", " ", fragment).strip()


def _html_to_markdown_body(html: str) -> str:
    """Best-effort HTML -> Markdown conversion for CodingGame statements."""
    md = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

    def _heading_repl(match: re.Match[str]) -> str:
        level = int(match.group(1))
        text = _clean_inline(match.group(2))
        if not text:
            return "\n"
        return f"\n\n{'#' * level} {text}\n\n"

    md = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", _heading_repl, md, flags=re.IGNORECASE | re.DOTALL)
    md = re.sub(r"<li[^>]*>", "\n- ", md, flags=re.IGNORECASE)
    md = re.sub(r"</li>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"<(br|hr)\s*/?>", "\n", md, flags=re.IGNORECASE)
    md = re.sub(r"</(p|div|section|article|table|tr|ul|ol|thead|tbody)>", "\n\n", md, flags=re.IGNORECASE)
    md = re.sub(r"<[^>]+>", "", md)
    md = unescape(md).replace("\xa0", " ")

    lines = [ln.rstrip() for ln in md.splitlines()]
    out: list[str] = []
    blank_run = 0
    pending_bullet = False
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            blank_run += 1
            if blank_run <= 2 and not pending_bullet:
                out.append("")
            continue

        # If a list item marker was isolated on its own line, attach it to the
        # next non-empty content line.
        if pending_bullet:
            out.append(f"- {stripped}")
            pending_bullet = False
            blank_run = 0
            continue

        if stripped in {"-", "*"}:
            pending_bullet = True
            blank_run = 0
            continue

        blank_run = 0
        # Remove HTML-layout indentation while preserving list markers.
        if re.match(r"^\s*[-*]\s+", ln):
            normalized = re.sub(r"^\s*[-*]\s+", "- ", ln)
            out.append(normalized.strip())
        else:
            out.append(stripped)

    if pending_bullet:
        out.append("- ")

    out = _restore_nested_bullets(out)
    return "\n".join(out).strip()


def _restore_nested_bullets(lines: list[str]) -> list[str]:
    """Recover simple nested list structure flattened by HTML stripping.

    Heuristic: when a top-level bullet ends with ':', following top-level bullets
    without ':' are treated as children until the next field-like bullet appears.
    """
    fixed: list[str] = []
    in_nested = False
    for line in lines:
        if re.match(r"^-\s+", line):
            text = line[2:].strip()
            if text.endswith(":"):
                fixed.append(line)
                in_nested = True
                continue

            if in_nested:
                # Next field header closes nested mode.
                if ":" in text:
                    fixed.append(line)
                    in_nested = text.endswith(":")
                else:
                    fixed.append(f"  - {text}")
                continue

            fixed.append(line)
            continue

        if line.strip() == "":
            fixed.append(line)
            continue

        # Narrative text ends nested list context.
        in_nested = False
        fixed.append(line)

    return fixed


def _statement_to_markdown(html: str) -> str:
    """Build markdown output starting directly at the converted full statement."""
    md_body = _html_to_markdown_body(html)
    return "## Full Statement (Converted)\n\n" + md_body + "\n"


def slug_from_url(url: str) -> str:
    """Extract the puzzle slug from a CodingGame URL."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    return parts[-1] if parts else url


def _extract_statement_from_obj(obj: dict) -> Optional[str]:
    """Best-effort extraction from known CodingGame payload shapes."""
    candidates = [
        obj.get("statement"),
        (obj.get("question") or {}).get("statement"),
        (obj.get("currentQuestion") or {}).get("statement"),
        ((obj.get("currentQuestion") or {}).get("question") or {}).get("statement"),
        (obj.get("puzzle") or {}).get("statement"),
    ]
    for item in candidates:
        if item:
            return str(item)
    return None


def _resolve_cg_user_id(
    puzzle_id: str,
    session: requests.Session,
    explicit_cg_user_id: Optional[int],
    env: Dict[str, str],
) -> Optional[int]:
    """Resolve CG user id from explicit arg, env, or authenticated IDE page."""
    if explicit_cg_user_id is not None:
        return explicit_cg_user_id

    env_user_id = (os.environ.get("CG_USER_ID") or env.get("CG_USER_ID", "")).strip()
    if env_user_id.isdigit():
        return int(env_user_id)

    ide_html = _get(IDE_URL.format(puzzle_id=puzzle_id), session)
    if not ide_html:
        return None

    m = re.search(r'"userId"\s*:\s*(\d+)', ide_html)
    if m:
        return int(m.group(1))

    return None


def _get_test_session_handle(puzzle_id: str, session: requests.Session, cg_user_id: Optional[int]) -> Optional[str]:
    """Resolve a short-lived test-session handle from puzzle slug."""
    result = _post(
        "Puzzle/generateSessionFromPuzzlePrettyId",
        [cg_user_id, puzzle_id, False],
        session,
    )
    if not result:
        return None

    inner = result.get("success") or result
    if not isinstance(inner, dict):
        return None

    handle = inner.get("handle") or inner.get("testSessionHandle") or inner.get("sessionHandle")
    if handle:
        return str(handle)

    # Older payloads may already contain statement-like data.
    statement = _extract_statement_from_obj(inner)
    if statement:
        return ""

    return None


def fetch_statement(
    puzzle_id: str,
    session: requests.Session,
    cg_user_id: Optional[int],
) -> tuple[Optional[str], Optional[str]]:
    """Get puzzle statement HTML via live test-session endpoint.

    Returns:
        (statement_html_or_none, question_title_or_none)
    """
    handle = _get_test_session_handle(puzzle_id, session, cg_user_id)
    if handle is None:
        return None, None

    # If handle is empty string, statement was embedded in legacy payload shape.
    if handle == "":
        legacy = _post(
            "Puzzle/generateSessionFromPuzzlePrettyId",
            [cg_user_id, puzzle_id, False],
            session,
        )
        if not legacy:
            return None, None
        inner_legacy = legacy.get("success") or legacy
        if isinstance(inner_legacy, dict):
            return _extract_statement_from_obj(inner_legacy), (inner_legacy.get("title") if isinstance(inner_legacy.get("title"), str) else None)
        return None, None

    result = _post(
        "TestSession/startTestSession",
        [handle],
        session,
    )
    if not result:
        return None, None

    inner = result.get("success") or result
    if not isinstance(inner, dict):
        return None, None

    question = (inner.get("currentQuestion") or {}).get("question") or {}
    question_title = question.get("title") if isinstance(question.get("title"), str) else None
    return _extract_statement_from_obj(inner), question_title


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
    parser.add_argument("--session", type=str, default=(os.environ.get("CG_SESSION") or env.get("CG_SESSION", "")))
    parser.add_argument("--cg-user-id", type=int, default=None, help="Optional CodingGame numeric userId.")
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()

    global _ssl_verify
    _ssl_verify = _resolve_verify_setting(args.no_verify, env)
    if _ssl_verify is False:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    elif isinstance(_ssl_verify, str):
        print(f"Using CA bundle: {_ssl_verify}")

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
        session_token = args.session.strip().strip('"').strip("'")
        # Send cookie in multiple compatible forms for CodingGame services.
        session.cookies.set("cgSession", session_token)
        session.cookies.set("cgSession", session_token, domain=".codingame.com")
        session.cookies.set("cgSession", session_token, domain="www.codingame.com")
        session.headers.update({"Cookie": f"cgSession={session_token}"})

    cg_user_id = _resolve_cg_user_id(puzzle_id, session, args.cg_user_id, env)
    if cg_user_id is not None:
        print(f"Using CG_USER_ID: {cg_user_id}")
    else:
        print("Using CG_USER_ID: <none>")

    print("Fetching puzzle statement ...")
    html, question_title = fetch_statement(puzzle_id, session, cg_user_id)

    if question_title:
        print(f"  Statement source question: {question_title}")

    if not html:
        print("  Could not retrieve statement via API.")
        print("  The game rules page is at:")
        print(f"    https://www.codingame.com/contests/{puzzle_id}")
        print("  Open it in a browser and copy the statement manually.")
        sys.exit(1)

    html_path = out_dir / "rules.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  Saved HTML: {html_path}")

    plain_text = _html_to_text(html)

    md_content = _statement_to_markdown(html)

    md_path = out_dir / "rules.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  Saved markdown: {md_path}")

    game_rules_dir = ensure_dir(ROOT / "games" / game)
    game_md_path = game_rules_dir / "rules.md"
    game_md_path.write_text(md_content, encoding="utf-8")
    print(f"  Saved game markdown: {game_md_path}")

    txt_path = out_dir / "rules.txt"
    txt_path.write_text(plain_text, encoding="utf-8")
    print(f"  Saved text: {txt_path}")


if __name__ == "__main__":
    main()
