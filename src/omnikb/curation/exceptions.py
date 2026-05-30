from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["info", "warn", "error"]


@dataclass(slots=True)
class CurationIssue:
    severity: Severity
    code: str
    message: str
    path: str | None = None


class CurationGateError(ValueError):
    """Raised when ingest is blocked by curation validation errors."""

    def __init__(self, issues: list[CurationIssue]) -> None:
        self.issues = issues
        errors = [i for i in issues if i.severity == "error"]
        super().__init__(f"Curation gate failed: {len(errors)} error(s)")
