"""Local TypeScript fix assistant using Ollama (llama3.2-based custom model).

Gathers ``tsconfig`` JSON, runs ``tsc -b`` in the TypeScript project root, and
sends diagnostics plus source to a local Ollama chat endpoint. Advisory-only:
prints the model response; does not write files.

Examples::

    ollama pull llama3.2
    ollama create ts-debugger -f ollama/typescript-debugger.Modelfile
    python docs/typescript-debug.py web/src/lib/api.ts
    python docs/typescript-debug.py web src/lib/api.ts --repo .
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - required for local `npx tsc` diagnostics
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _resolve_repo_root(repo: str) -> Path:
    root = Path(repo).resolve()
    if not root.is_dir():
        msg = f"Repository root is not a directory: {root}"
        raise SystemExit(msg)
    return root


def _safe_under_repo(repo: Path, candidate: Path) -> Path:
    """Resolve candidate and ensure it stays under repo (no path traversal)."""
    resolved = (repo / candidate).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        msg = f"Path escapes repository root: {candidate}"
        raise SystemExit(msg) from exc
    return resolved


def find_ts_project_root(repo: Path, start_from: Path) -> Path:
    """Walk parents from ``start_from`` (file or dir) until ``tsconfig.json``."""
    repo_resolved = repo.resolve()
    cur = (start_from.parent if start_from.is_file() else start_from).resolve()
    for _ in range(200):
        try:
            cur.relative_to(repo_resolved)
        except ValueError:
            break
        if (cur / "tsconfig.json").is_file():
            return cur
        if cur == repo_resolved or cur.parent == cur:
            break
        cur = cur.parent
    msg = f"No tsconfig.json found walking up from {start_from}"
    raise SystemExit(msg)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def collect_tsconfig_bundle(ts_root: Path) -> str:
    """Include root tsconfig and referenced JSON files when present."""
    parts: list[str] = []
    root_cfg = ts_root / "tsconfig.json"
    if not root_cfg.is_file():
        msg = f"Missing tsconfig.json in {ts_root}"
        raise SystemExit(msg)
    parts.append(f"### {root_cfg.name}\n```json\n{read_text(root_cfg)}\n```")

    try:
        data: dict[str, Any] = json.loads(read_text(root_cfg))
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in {root_cfg}: {exc}"
        raise SystemExit(msg) from exc

    for ref in data.get("references") or []:
        if not isinstance(ref, dict):
            continue
        rel = ref.get("path")
        if not isinstance(rel, str):
            continue
        ref_path = (ts_root / rel).resolve()
        if not str(ref_path).startswith(str(ts_root.resolve())):
            continue
        if ref_path.is_file():
            parts.append(f"### {ref_path.name}\n```json\n{read_text(ref_path)}\n```")
    return "\n\n".join(parts)


def run_tsc(ts_root: Path) -> tuple[int, str]:
    """Run TypeScript solution build in ``ts_root`` (no emit from project refs)."""
    proc = subprocess.run(  # nosec B603 B607 - fixed command/cwd, no shell, local dev helper
        ["npx", "tsc", "-b", "--pretty", "false"],
        cwd=str(ts_root),
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def ollama_chat(
    base_url: str,
    model: str,
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
) -> str:
    """Call Ollama ``/api/chat`` (non-streaming) and return assistant message text."""
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"Unsupported Ollama URL scheme for {base_url!r}; use http(s)."
        raise SystemExit(msg)

    url = base_url.rstrip("/") + "/api/chat"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:  # nosec B310 - scheme validated above
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        msg = f"Ollama HTTP {exc.code}: {detail}"
        raise SystemExit(msg) from exc
    except urllib.error.URLError as exc:
        msg = (
            f"Could not reach Ollama at {url}: {exc}\n"
            "Ensure Ollama is running and the model exists "
            f"(e.g. `ollama create {model} -f ollama/typescript-debugger.Modelfile`)."
        )
        raise SystemExit(msg) from exc

    message_block = payload.get("message") or {}
    content = message_block.get("content") if isinstance(message_block, dict) else None
    if not isinstance(content, str):
        err = f"Unexpected Ollama response: {payload!r}"
        raise SystemExit(err)
    return content


def build_user_prompt(
    *,
    rel_display: str,
    tsconfig_block: str,
    source: str,
    tsc_exit: int,
    tsc_output: str,
    extra_errors: str | None,
) -> str:
    extra = ""
    if extra_errors and extra_errors.strip():
        extra = textwrap.dedent(
            f"""

            Additional notes / pasted diagnostics from the user:
            ```
            {extra_errors.strip()}
            ```
            """
        )
    return textwrap.dedent(
        f"""
        TypeScript project ``tsconfig`` bundle:
        {tsconfig_block}

        Primary target file: `{rel_display}`

        Current source:
        ```ts
        {source}
        ```

        Output of `npx tsc -b --pretty false` in the project root (exit {tsc_exit}):
        ```
        {tsc_output.strip() or "(no output)"}
        ```
        {extra}

        Respond with: (1) plain-English summary of each relevant error, (2) minimal fix
        as a unified diff or a single full-file ```ts block for `{rel_display}` only.
        """
    ).strip()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send TypeScript diagnostics + source to a local Ollama model.",
    )
    parser.add_argument(
        "target",
        help="Path to .ts/.tsx file: repo-relative (e.g. web/src/lib/api.ts), "
        "or first arg of two-arg form: TS_ROOT (directory containing tsconfig.json).",
    )
    parser.add_argument(
        "path_in_project",
        nargs="?",
        default=None,
        help="If set with TS_ROOT-style first arg: file relative to TS_ROOT (e.g. src/lib/api.ts).",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--model",
        default="ts-debugger",
        help="Ollama model name (default: ts-debugger).",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Ollama API base URL (default: http://127.0.0.1:11434).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0).",
    )
    parser.add_argument(
        "--no-tsc",
        action="store_true",
        help="Skip running tsc; only send source and tsconfig (optional pasted errors).",
    )
    parser.add_argument(
        "--extra-errors",
        default="",
        help="Extra static error text to include in the prompt (e.g. pasted tsc output).",
    )
    parser.add_argument(
        "--system",
        default="",
        help="Optional extra system instructions (appended to default system prompt).",
    )
    return parser.parse_args(argv)


def resolve_target_paths(args: argparse.Namespace, repo: Path) -> tuple[Path, Path]:
    """Return (absolute_target_file, ts_project_root)."""
    # Two-arg legacy: TS_ROOT + path inside project
    if args.path_in_project is not None:
        ts_sub = Path(args.target)
        inner = Path(args.path_in_project)
        ts_root = _safe_under_repo(repo, ts_sub)
        if not ts_root.is_dir():
            msg = f"TypeScript root is not a directory: {ts_root}"
            raise SystemExit(msg)
        target = _safe_under_repo(repo, ts_sub / inner)
    else:
        target = _safe_under_repo(repo, Path(args.target))
    if not target.is_file():
        msg = f"Target is not a file: {target}"
        raise SystemExit(msg)
    suffix = target.suffix.lower()
    if suffix not in {".ts", ".tsx", ".mts", ".cts"}:
        msg = f"Target should be a TypeScript file, got: {target}"
        raise SystemExit(msg)
    ts_root = find_ts_project_root(repo, target)
    return target, ts_root


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = _resolve_repo_root(args.repo)
    target, ts_root = resolve_target_paths(args, repo)

    try:
        rel_display = str(target.relative_to(repo))
    except ValueError:
        rel_display = str(target)

    tsconfig_block = collect_tsconfig_bundle(ts_root)
    source = read_text(target)

    if args.no_tsc:
        tsc_exit, tsc_out = 0, "(skipped: --no-tsc)"
    else:
        tsc_exit, tsc_out = run_tsc(ts_root)

    user_prompt = build_user_prompt(
        rel_display=rel_display,
        tsconfig_block=tsconfig_block,
        source=source,
        tsc_exit=tsc_exit,
        tsc_output=tsc_out,
        extra_errors=args.extra_errors or None,
    )

    default_system = "You fix TypeScript using only the provided project context and diagnostics."
    system = (
        default_system if not args.system.strip() else f"{default_system}\n\n{args.system.strip()}"
    )

    print(f"--- Ollama model: {args.model} @ {args.ollama_url} ---", file=sys.stderr)
    print(f"--- TS project root: {ts_root} ---", file=sys.stderr)
    print(f"--- Target: {target} ---", file=sys.stderr)

    reply = ollama_chat(
        args.ollama_url,
        args.model,
        system,
        user_prompt,
        temperature=args.temperature,
    )
    print("\n--- Assistant ---\n")
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
