"""Layer 1 memory_tier assignment and boost eligibility (ADR 0003)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

MemoryTier = Literal["curated_note", "reference_pdf", "samples", "staging", "default"]

EventType = Literal["query_impression", "result_click", "result_expand"]

_EVENT_WEIGHTS: dict[str, float] = {
    "query_impression": 1.0,
    "result_click": 3.0,
    "result_expand": 2.0,
}


def normalize_source_path(source_path: str) -> str:
    return source_path.replace("\\", "/").lstrip("./")


def assign_memory_tier(source_path: str, file_type: str | None = None) -> MemoryTier:
    """Assign memory_tier from source path and optional file type suffix."""
    path = normalize_source_path(source_path)
    posix = PurePosixPath(path)
    parts = {p.lower() for p in posix.parts}
    name = posix.name.lower()
    suffix = (file_type or posix.suffix.lstrip(".")).lower()

    if "_samples" in parts or name.startswith("sample-"):
        return "samples"
    if "staging" in parts:
        return "staging"
    if suffix == "pdf" or posix.suffix.lower() == ".pdf":
        return "reference_pdf"
    if "curated" in parts and posix.suffix.lower() == ".md":
        return "curated_note"
    return "default"


def boost_allowed(memory_tier: str, event_type: str) -> bool:
    """Return whether this event should update chunk_boosts for the tier."""
    if memory_tier == "samples" or memory_tier == "staging":
        return False
    if memory_tier == "reference_pdf" and event_type == "query_impression":
        return False
    return event_type in _EVENT_WEIGHTS


def event_weight(event_type: str) -> float:
    return _EVENT_WEIGHTS.get(event_type, 0.0)


def dreaming_allowed(memory_tier: str, *, has_click_boost: bool) -> bool:
    if memory_tier in ("samples", "staging"):
        return False
    if memory_tier == "reference_pdf":
        return has_click_boost
    return True
