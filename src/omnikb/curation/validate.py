from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from omnikb.adapters.document_loader import SUPPORTED_SUFFIXES, load_document

Severity = Literal["info", "warn", "error"]


@dataclass(slots=True)
class CurationIssue:
    severity: Severity
    code: str
    message: str
    path: str | None = None


@dataclass(slots=True)
class ValidationReport:
    issues: list[CurationIssue] = field(default_factory=list)
    duplicate_content_hashes: dict[str, list[str]] = field(default_factory=dict)
    entries_scanned: int = 0


def _default_max_bytes() -> int:
    return 25 * 1024 * 1024


def validate_corpus(
    root: Path,
    *,
    recursive: bool = True,
    max_file_bytes: int | None = None,
) -> ValidationReport:
    """
    Dry-run validation: supported types, empty content, size limits, duplicate hashes.

    Does not mutate the filesystem or vector store.
    """
    max_b = max_file_bytes if max_file_bytes is not None else _default_max_bytes()
    report = ValidationReport()
    if not root.exists():
        report.issues.append(
            CurationIssue(
                severity="error",
                code="root_missing",
                message=f"Root path does not exist: {root}",
                path=str(root),
            )
        )
        return report

    hash_to_paths: dict[str, list[str]] = defaultdict(list)
    seen_lower: dict[str, str] = {}

    iterator = root.rglob("*") if recursive else root.glob("*")
    for path in sorted(p for p in iterator if p.is_file()):
        suffix = path.suffix.lower()
        rel = str(path).replace("\\", "/")
        if suffix not in SUPPORTED_SUFFIXES:
            report.issues.append(
                CurationIssue(
                    severity="info",
                    code="unsupported_suffix",
                    message=f"Skipped unsupported type {suffix!r}",
                    path=rel,
                )
            )
            continue

        key_lower = rel.lower()
        if key_lower in seen_lower and seen_lower[key_lower] != rel:
            report.issues.append(
                CurationIssue(
                    severity="warn",
                    code="case_collision",
                    message=(
                        f"Possible case-only path collision: {rel!r} vs {seen_lower[key_lower]!r}"
                    ),
                    path=rel,
                )
            )
        seen_lower[key_lower] = rel

        try:
            stat = path.stat()
        except OSError as exc:
            report.issues.append(
                CurationIssue(
                    severity="error",
                    code="stat_failed",
                    message=f"Could not stat file: {exc}",
                    path=rel,
                )
            )
            continue

        if stat.st_size > max_b:
            report.issues.append(
                CurationIssue(
                    severity="warn",
                    code="large_file",
                    message=f"File size {stat.st_size} bytes exceeds threshold {max_b}",
                    path=rel,
                )
            )

        try:
            doc = load_document(path)
        except Exception as exc:  # noqa: BLE001 - surface extraction failures
            report.issues.append(
                CurationIssue(
                    severity="error",
                    code="load_failed",
                    message=f"Failed to load document: {exc}",
                    path=rel,
                )
            )
            continue

        report.entries_scanned += 1
        hash_to_paths[doc.content_hash].append(rel)

        if not doc.text.strip():
            report.issues.append(
                CurationIssue(
                    severity="error",
                    code="empty_content",
                    message="Extracted text is empty or whitespace-only",
                    path=rel,
                )
            )

    for digest, paths in hash_to_paths.items():
        if len(paths) > 1:
            report.duplicate_content_hashes[digest] = sorted(paths)
            report.issues.append(
                CurationIssue(
                    severity="warn",
                    code="duplicate_content_hash",
                    message=f"Same content_hash appears under {len(paths)} paths",
                    path=paths[0],
                )
            )

    return report


def report_to_dict(report: ValidationReport) -> dict[str, Any]:
    return {
        "entries_scanned": report.entries_scanned,
        "issue_count": len(report.issues),
        "issues": [
            {
                "severity": i.severity,
                "code": i.code,
                "message": i.message,
                "path": i.path,
            }
            for i in report.issues
        ],
        "duplicate_content_hashes": report.duplicate_content_hashes,
    }
