from __future__ import annotations

import fnmatch
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from omnikb.adapters.document_loader import SUPPORTED_SUFFIXES, load_document
from omnikb.curation.exceptions import CurationGateError, CurationIssue
from omnikb.curation.frontmatter import as_bool, parse_frontmatter

Severity = Literal["info", "warn", "error"]


@dataclass(slots=True)
class ValidationReport:
    issues: list[CurationIssue] = field(default_factory=list)
    duplicate_content_hashes: dict[str, list[str]] = field(default_factory=dict)
    entries_scanned: int = 0


@dataclass(slots=True)
class CurationPolicy:
    gate_enabled: bool = True
    gate_roots: list[str] = field(default_factory=lambda: ["curated"])
    exempt_globs: list[str] = field(default_factory=lambda: ["_samples/**", "sample-*"])
    strict_frontmatter: bool = True


_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"password\s*=\s*\S+"),
    re.compile(r"api_key\s*=\s*\S+"),
]


def _default_max_bytes() -> int:
    return 25 * 1024 * 1024


def _is_exempt(rel_posix: str, exempt_globs: list[str]) -> bool:
    name = rel_posix.split("/")[-1]
    for pattern in exempt_globs:
        if fnmatch.fnmatch(rel_posix, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False


def _scan_secrets(raw_text: str, rel: str) -> list[CurationIssue]:
    issues: list[CurationIssue] = []
    for pat in _SECRET_PATTERNS:
        if pat.search(raw_text):
            issues.append(
                CurationIssue(
                    severity="error",
                    code="secret_pattern",
                    message=f"Potential secret matched pattern {pat.pattern!r}",
                    path=rel,
                )
            )
    return issues


def validate_frontmatter(path: Path, policy: CurationPolicy) -> list[CurationIssue]:
    """Check .md frontmatter fields and file text for gate compliance."""
    if not policy.strict_frontmatter:
        return []

    rel = str(path).replace("\\", "/")
    issues: list[CurationIssue] = []

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            CurationIssue(
                severity="error",
                code="read_failed",
                message=f"Could not read file: {exc}",
                path=rel,
            )
        ]

    fm = parse_frontmatter(path)
    if fm is None:
        issues.append(
            CurationIssue(
                severity="error",
                code="missing_frontmatter",
                message="No YAML frontmatter block found",
                path=rel,
            )
        )
    else:
        if as_bool(fm.get("kb_ingest")) is not True:
            issues.append(
                CurationIssue(
                    severity="error",
                    code="kb_ingest_not_true",
                    message="kb_ingest must be true",
                    path=rel,
                )
            )
        if as_bool(fm.get("note_finalized")) is not True:
            issues.append(
                CurationIssue(
                    severity="error",
                    code="note_not_finalized",
                    message="note_finalized must be true",
                    path=rel,
                )
            )
        if fm.get("kb_status") != "curated":
            issues.append(
                CurationIssue(
                    severity="error",
                    code="kb_status_not_curated",
                    message="kb_status must be 'curated'",
                    path=rel,
                )
            )
        ai_verified = as_bool(fm.get("ai_summary_verified"))
        if as_bool(fm.get("ai_assisted")) is True and ai_verified is not True:
            issues.append(
                CurationIssue(
                    severity="error",
                    code="ai_unverified",
                    message="ai_assisted is true but ai_summary_verified is not true",
                    path=rel,
                )
            )

        if not fm.get("summary"):
            issues.append(
                CurationIssue(
                    severity="warn",
                    code="missing_summary",
                    message="summary field is empty or absent",
                    path=rel,
                )
            )
        if not fm.get("kb_reviewed_at"):
            issues.append(
                CurationIssue(
                    severity="warn",
                    code="missing_kb_reviewed_at",
                    message="kb_reviewed_at not set",
                    path=rel,
                )
            )

    issues.extend(_scan_secrets(raw, rel))
    return issues


def _gate_applies(rel_from_root: str, root: Path, policy: CurationPolicy) -> bool:
    if not policy.gate_enabled:
        return False
    gate_set = set(policy.gate_roots)
    root_is_gate = root.name in gate_set
    under_gate = root_is_gate or rel_from_root.split("/")[0] in gate_set
    return under_gate and not _is_exempt(rel_from_root, policy.exempt_globs)


def _validate_one_file(
    path: Path,
    *,
    scan_root: Path,  # noqa: ARG001 — reserved for scan-relative reporting
    corpus_root: Path,
    policy: CurationPolicy,
    max_bytes: int,
    report: ValidationReport,
    hash_to_paths: dict[str, list[str]],
) -> None:
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
        return

    try:
        rel_from_corpus = str(path.relative_to(corpus_root)).replace("\\", "/")
    except ValueError:
        rel_from_corpus = path.name

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
        return

    if stat.st_size > max_bytes:
        report.issues.append(
            CurationIssue(
                severity="warn",
                code="large_file",
                message=f"File size {stat.st_size} bytes exceeds threshold {max_bytes}",
                path=rel,
            )
        )

    if suffix == ".md" and _gate_applies(rel_from_corpus, corpus_root, policy):
        report.issues.extend(validate_frontmatter(path, policy))
    elif suffix == ".txt" and _gate_applies(rel_from_corpus, corpus_root, policy):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            report.issues.append(
                CurationIssue(
                    severity="error",
                    code="read_failed",
                    message=f"Could not read file: {exc}",
                    path=rel,
                )
            )
        else:
            report.issues.extend(_scan_secrets(raw, rel))

    try:
        doc = load_document(path)
    except Exception as exc:  # noqa: BLE001
        report.issues.append(
            CurationIssue(
                severity="error",
                code="load_failed",
                message=f"Failed to load document: {exc}",
                path=rel,
            )
        )
        return

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


def validate_ingest_files(
    files: list[Path],
    *,
    corpus_root: Path,
    policy: CurationPolicy | None = None,
    max_file_bytes: int | None = None,
) -> ValidationReport:
    """Validate only the given files (for single-file ingest gate)."""
    _policy = policy if policy is not None else CurationPolicy()
    max_b = max_file_bytes if max_file_bytes is not None else _default_max_bytes()
    report = ValidationReport()
    hash_to_paths: dict[str, list[str]] = defaultdict(list)
    for path in sorted(files):
        _validate_one_file(
            path,
            scan_root=corpus_root,
            corpus_root=corpus_root,
            policy=_policy,
            max_bytes=max_b,
            report=report,
            hash_to_paths=hash_to_paths,
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


def curation_errors(report: ValidationReport) -> list[CurationIssue]:
    return [issue for issue in report.issues if issue.severity == "error"]


def assert_curation_gate(
    report: ValidationReport,
    *,
    allow_override: bool,
    override_enabled: bool,
) -> None:
    if allow_override and override_enabled:
        return
    errors = curation_errors(report)
    if errors:
        raise CurationGateError(errors)


def validate_corpus(
    root: Path,
    *,
    recursive: bool = True,
    max_file_bytes: int | None = None,
    policy: CurationPolicy | None = None,
) -> ValidationReport:
    """
    Dry-run validation: supported types, empty content, size limits, duplicate hashes.

    Does not mutate the filesystem or vector store.
    """
    _policy = policy if policy is not None else CurationPolicy()
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
        rel = str(path).replace("\\", "/")
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

        _validate_one_file(
            path,
            scan_root=root,
            corpus_root=root,
            policy=_policy,
            max_bytes=max_b,
            report=report,
            hash_to_paths=hash_to_paths,
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
