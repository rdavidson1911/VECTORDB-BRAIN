from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(slots=True)
class ChunkingConfig:
    strategy: str = "recursive_char_v1"
    chunk_size: int = 450
    chunk_overlap: int = 60
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " "])
    min_chunk_size: int = 32


def chunk_text(text: str, config: ChunkingConfig) -> list[str]:
    if config.strategy == "markdown_structure_v1":
        return _markdown_structure_chunks(
            text=text,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            min_chunk_size=config.min_chunk_size,
        )
    if config.strategy == "token_recursive_v1":
        # Token-aware approximation for local-first performance without extra tokenizer deps.
        token_text = " ".join(text.split())
        return recursive_chunk_text(
            token_text,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=[". ", " ", "\n"],
            min_chunk_size=config.min_chunk_size,
        )
    return recursive_chunk_text(
        text,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=config.separators,
        min_chunk_size=config.min_chunk_size,
    )


def recursive_chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str] | None = None,
    min_chunk_size: int = 32,
) -> list[str]:
    if not text.strip():
        return []

    separators = separators or ["\n\n", "\n", ". ", " "]
    pieces = _split_recursive(text, separators, chunk_size)

    merged = _merge_small_pieces(pieces, chunk_size, min_chunk_size=min_chunk_size)
    if chunk_overlap <= 0:
        return merged

    return _apply_overlap(merged, chunk_overlap)


def _split_recursive(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size or not separators:
        return [text.strip()]

    sep = separators[0]
    parts = text.split(sep)
    if len(parts) == 1:
        return _split_recursive(text, separators[1:], chunk_size)

    chunks: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= chunk_size:
            chunks.append(part)
        else:
            chunks.extend(_split_recursive(part, separators[1:], chunk_size))
    return chunks


def _merge_small_pieces(
    pieces: Iterable[str], chunk_size: int, min_chunk_size: int = 32
) -> list[str]:
    merged: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current} {piece}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            merged.append(current)
        current = piece
    if current:
        merged.append(current)
    return _coalesce_tiny_chunks(merged, min_chunk_size=min_chunk_size, max_chunk_size=chunk_size)


def _apply_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    if not chunks:
        return []
    overlapped = [chunks[0]]
    for index in range(1, len(chunks)):
        prefix = chunks[index - 1][-overlap_chars:]
        overlapped.append(f"{prefix} {chunks[index]}".strip())
    return overlapped


def _coalesce_tiny_chunks(chunks: list[str], min_chunk_size: int, max_chunk_size: int) -> list[str]:
    if not chunks:
        return []
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < min_chunk_size:
            candidate = f"{merged[-1]} {chunk}".strip()
            if len(candidate) <= max_chunk_size:
                merged[-1] = candidate
                continue
        merged.append(chunk)
    return merged


def _markdown_structure_chunks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
    min_chunk_size: int,
) -> list[str]:
    sections: list[str] = []
    current_section: list[str] = []
    for line in text.splitlines():
        is_heading = line.lstrip().startswith("#")
        if is_heading and current_section:
            sections.append("\n".join(current_section).strip())
            current_section = [line]
            continue
        current_section.append(line)
    if current_section:
        sections.append("\n".join(current_section).strip())

    chunks: list[str] = []
    for section in sections:
        if not section:
            continue
        if len(section) <= chunk_size:
            chunks.append(section)
            continue
        chunks.extend(
            recursive_chunk_text(
                section,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators,
                min_chunk_size=min_chunk_size,
            )
        )
    return chunks
