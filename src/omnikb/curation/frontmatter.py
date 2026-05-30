from __future__ import annotations

import re
from pathlib import Path

_FENCE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
_KV = re.compile(r"^([\w][\w_-]*)[ \t]*:[ \t]*(.*)$")
_BOOL_TRUE = frozenset({"true", "yes", "on"})
_BOOL_FALSE = frozenset({"false", "no", "off"})


def _coerce(raw: str) -> bool | str | None:
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1].strip()
    lower = s.lower()
    if lower in _BOOL_TRUE:
        return True
    if lower in _BOOL_FALSE:
        return False
    return s if s else None


def as_bool(value: object) -> bool | None:
    """Interpret frontmatter scalar as bool (handles quoted true/false strings)."""
    if value is True or value is False:
        return value
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in _BOOL_TRUE:
            return True
        if lower in _BOOL_FALSE:
            return False
    return None


def parse_frontmatter(path: Path) -> dict[str, object] | None:
    """Return parsed YAML frontmatter dict, or None if absent or malformed. Never raises."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    m = _FENCE.match(text)
    if m is None:
        return None
    result: dict[str, object] = {}
    for line in m.group(1).splitlines():
        kv = _KV.match(line)
        if kv:
            result[kv.group(1)] = _coerce(kv.group(2))
    return result


def frontmatter_body(path: Path) -> str:
    """Return file content below the frontmatter fence (full text if no fence present)."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    m = _FENCE.match(text)
    return text[m.end() :] if m else text
