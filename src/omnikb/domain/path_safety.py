"""Sanitize and normalize user-supplied ingest paths (POSIX + Windows)."""

from __future__ import annotations

import re
from pathlib import Path

# Control chars, null bytes, shell/sql-adjacent metacharacters in paths.
_FORBIDDEN_IN_PATH = re.compile(r"[\x00-\x1f\x7f;|`$&<>\"'\\]+")
_WINDOWS_DRIVE = re.compile(r"^[a-zA-Z]:")
_SOURCES_MARKER = "/data/sources/"


class UnsafePathError(ValueError):
    """Raised when user input fails path safety checks."""


def _ensure_leading_sources_marker(normalized: str) -> str:
    """
    Map ``data/sources/...`` (no leading slash) to ``/data/sources/...``.

    Without this, ``allowed_root / "data/sources/foo"`` doubles the segment.
    """
    text = normalized.strip()
    if text.startswith("/"):
        return normalized
    lower = text.lower()
    if lower == "data/sources" or lower.startswith("data/sources/"):
        return f"/{text}"
    return normalized


def normalize_path_slashes(raw: str) -> str:
    """Collapse user input to forward slashes without resolving yet."""
    text = raw.strip().strip('"').strip("'")
    text = text.replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    return text


def sanitize_path_input(raw: str) -> str:
    """
    Reject obviously dangerous path strings before filesystem access.

    Not a substitute for root confinement — always call `resolve_under_allowed_root`.
    """
    if not raw or not raw.strip():
        raise UnsafePathError("Path is required.")
    if "\x00" in raw:
        raise UnsafePathError("Path contains null bytes.")
    normalized = normalize_path_slashes(raw)
    if _FORBIDDEN_IN_PATH.search(normalized):
        raise UnsafePathError("Path contains disallowed characters.")
    if ".." in normalized.split("/"):
        raise UnsafePathError("Path traversal (..) is not allowed.")
    lowered = normalized.lower()
    if lowered.startswith(("http://", "https://", "file://", "ftp://")):
        raise UnsafePathError("URL paths are not allowed.")
    return normalized


def _map_via_sources_marker(normalized: str, container_root: str) -> str | None:
    """
      Map any path that includes a ``/data/sources/`` segment to the configured container root.

      Enables ``I:/.../data/sources/file.pdf`` → ``/data/sources/file.pdf`` in Docker without
    ``HOST_DATA_SOURCES_PATH``.
    """
    lower = normalized.lower()
    idx = lower.find(_SOURCES_MARKER)
    if idx < 0:
        return None
    suffix = normalized[idx + len(_SOURCES_MARKER) :].lstrip("/")
    container = normalize_path_slashes(container_root).rstrip("/")
    return f"{container}/{suffix}" if suffix else container


def map_host_path_to_container(
    normalized: str,
    *,
    container_root: str,
    host_root: str | None,
) -> str:
    """
    Map a Windows/host path under `host_root` to the container bind mount (`container_root`).

    Example: host `I:/VECTORDB-BRAIN/data/sources/foo.md` → `/data/sources/foo.md`
    """
    container = normalize_path_slashes(container_root).rstrip("/")
    if not host_root:
        marker_path = _map_via_sources_marker(normalized, container)
        return marker_path if marker_path is not None else normalized

    host = normalize_path_slashes(host_root).rstrip("/")
    norm_lower = normalized.lower()
    host_lower = host.lower()

    if norm_lower == host_lower or norm_lower.startswith(host_lower + "/"):
        suffix = normalized[len(host) :].lstrip("/")
        return f"{container}/{suffix}" if suffix else container

    # Windows drive path that matches host root by suffix (case-insensitive)
    if _WINDOWS_DRIVE.match(normalized):
        without_drive = normalized.split(":", 1)[1].lstrip("/")
        host_without_drive = host.split(":", 1)[-1].lstrip("/")
        if without_drive.lower() == host_without_drive.lower() or without_drive.lower().startswith(
            host_without_drive.lower() + "/"
        ):
            suffix = without_drive[len(host_without_drive) :].lstrip("/")
            return f"{container}/{suffix}" if suffix else container

    marker_path = _map_via_sources_marker(normalized, container)
    if marker_path is not None:
        return marker_path

    return normalized


def resolve_ingest_path(
    raw: str,
    *,
    allowed_root: Path,
    host_sources_root: str | None = None,
) -> Path:
    """
    Sanitize, map host→container paths, and resolve to a path under `allowed_root`.
    """
    cleaned = _ensure_leading_sources_marker(sanitize_path_input(raw))
    root = allowed_root.resolve()
    mapped = map_host_path_to_container(
        cleaned,
        container_root=root.as_posix(),
        host_root=host_sources_root,
    )
    if mapped.startswith("/") or _WINDOWS_DRIVE.match(mapped):
        candidate = Path(mapped)
    else:
        candidate = root / mapped

    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise UnsafePathError(f"Cannot resolve path: {mapped}") from exc

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("Path must stay under the configured sources directory.") from exc

    return resolved


def assert_ingest_file_target(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Source path does not exist: {path.as_posix()}")
    if not path.is_file():
        raise UnsafePathError("Single-file ingest requires a file path, not a directory.")
