from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from omnikb.config.settings import get_settings

_log = logging.getLogger(__name__)
_lock = Lock()


def _logs_root() -> Path:
    settings = get_settings()
    root = Path(settings.logs_dir)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def append_jsonl(stream: str, record: dict[str, Any]) -> None:
    """Append one JSON object as a line to logs/{stream}-YYYY-MM-DD.jsonl."""
    settings = get_settings()
    if stream.startswith("api-") and not settings.request_logging_enabled:
        return
    if stream.startswith("ui-") and not settings.ui_logging_enabled:
        return

    stamped = {
        "logged_at": datetime.now(UTC).isoformat(),
        **record,
    }
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    path = _logs_root() / f"{stream}-{day}.jsonl"
    line = json.dumps(stamped, default=str) + "\n"
    try:
        with _lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
    except OSError as exc:
        _log.warning("Failed to write log %s: %s", path, exc)
