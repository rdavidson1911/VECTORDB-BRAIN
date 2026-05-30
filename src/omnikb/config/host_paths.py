"""Derive optional host bind-mount path for ingest path mapping."""

from __future__ import annotations

from pathlib import Path

_DOCKER_SOURCES_POSIX = "/data/sources"


def canonical_data_sources_path(configured: str) -> str:
    """
    Resolve ``DATA_SOURCES_PATH`` for the running process.

    When the API runs inside Docker, the bind mount at ``/data/sources`` wins over
    ``./data/sources`` from ``.env`` (which would otherwise resolve under ``/app``).
    """
    configured = configured.strip()
    docker_mount = Path(_DOCKER_SOURCES_POSIX)
    if docker_mount.is_dir():
        return _DOCKER_SOURCES_POSIX
    path = Path(configured)
    try:
        if path.is_absolute():
            return str(path.resolve())
        return str((Path.cwd() / path).resolve())
    except OSError:
        return configured


def resolve_host_sources_root(explicit_host: str, data_sources_path: str) -> str | None:
    """
    Return host path used to map Windows paths into ``data_sources_path``.

    Uses ``HOST_DATA_SOURCES_PATH`` when set; otherwise infers from a relative or absolute
    ``DATA_SOURCES_PATH`` on the machine running the API (not the in-container ``/data/sources``).
    """
    if explicit_host.strip():
        return explicit_host.strip()

    dsp = Path(data_sources_path)
    if dsp.as_posix().replace("\\", "/").rstrip("/") == _DOCKER_SOURCES_POSIX:
        return None

    try:
        resolved = dsp.resolve() if dsp.is_absolute() else (Path.cwd() / dsp).resolve()
    except OSError:
        return None

    if resolved.exists():
        return str(resolved)
    return None
