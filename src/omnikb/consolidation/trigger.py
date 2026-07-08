"""Explicit API-driven L2 consolidation trigger (ADR: consolidation-trigger-analysis.md)."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

log = logging.getLogger(__name__)

JobStatus = Literal["accepted", "running", "completed", "failed"]


@dataclass(slots=True)
class ConsolidationJob:
    """In-memory consolidation run record (prototype; replace with durable store later)."""

    job_id: str
    accepted_at: str
    status: JobStatus
    scope: str | None = None
    dry_run: bool = False
    reason: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    message: str | None = None
    error: str | None = None


@dataclass
class ConsolidationTriggerService:
    """Single-flight consolidation trigger; runs work off the request thread."""

    enabled: bool = True
    min_chunk_threshold: int = 0
    _flight_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _active_job_id: str | None = field(default=None, repr=False)
    _jobs: dict[str, ConsolidationJob] = field(default_factory=dict, repr=False)

    def submit_run(
        self,
        *,
        scope: str | None = None,
        dry_run: bool = False,
        reason: str | None = None,
    ) -> ConsolidationJob:
        """Accept a consolidation run or raise if disabled / single-flight busy."""
        if not self.enabled:
            raise ConsolidationDisabledError("Consolidation trigger is disabled.")
        if not self._flight_lock.acquire(blocking=False):
            raise ConsolidationBusyError("Another consolidation job is already running.")
        try:
            if self._active_job_id is not None:
                self._flight_lock.release()
                raise ConsolidationBusyError("Another consolidation job is already running.")
            job_id = str(uuid.uuid4())
            accepted_at = _utc_now_iso()
            job = ConsolidationJob(
                job_id=job_id,
                accepted_at=accepted_at,
                status="accepted",
                scope=scope,
                dry_run=dry_run,
                reason=reason,
            )
            self._jobs[job_id] = job
            self._active_job_id = job_id
            thread = threading.Thread(
                target=self._run_job,
                args=(job_id,),
                name=f"consolidation-{job_id[:8]}",
                daemon=True,
            )
            thread.start()
            return job
        except Exception:
            if self._flight_lock.locked():
                self._flight_lock.release()
            raise

    def get_job(self, job_id: str) -> ConsolidationJob | None:
        return self._jobs.get(job_id)

    def _run_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            self._release_flight()
            return
        job.status = "running"
        job.started_at = _utc_now_iso()
        try:
            if job.dry_run:
                job.message = "dry_run: no consolidation side effects applied"
            else:
                # L2 episodic merge not implemented yet; trigger contract only.
                job.message = (
                    "consolidation_stub: trigger executed; episodic store pipeline not wired"
                )
            job.status = "completed"
            job.finished_at = _utc_now_iso()
            log.info(
                "consolidation_job_finished",
                extra={
                    "job_id": job_id,
                    "dry_run": job.dry_run,
                    "reason": job.reason,
                },
            )
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = _utc_now_iso()
            log.exception("consolidation_job_failed", extra={"job_id": job_id})
        finally:
            self._release_flight()

    def _release_flight(self) -> None:
        self._active_job_id = None
        if self._flight_lock.locked():
            self._flight_lock.release()


class ConsolidationDisabledError(Exception):
    """Raised when consolidation is turned off via configuration."""


class ConsolidationBusyError(Exception):
    """Raised when single-flight lock is held by another job."""


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
