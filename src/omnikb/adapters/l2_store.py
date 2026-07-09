from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path


class L2StoreAdapter:
    """SQLite-backed Layer 2 episodic session store.

    Per-method connections keep the adapter thread-safe and compatible with
    SQLite WAL mode under concurrent readers.
    """

    def __init__(self, db_path: str = "data/l2_sessions.db") -> None:
        self._db_path = db_path
        self._ensure_schema()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    label      TEXT,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id       TEXT    NOT NULL,
                    artifact_type    TEXT    NOT NULL,
                    text_content     TEXT    NOT NULL,
                    source_chunk_ids TEXT    NOT NULL DEFAULT '[]',
                    metadata_json    TEXT    NOT NULL DEFAULT '{}',
                    created_at       REAL    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_artifacts_session
                    ON artifacts(session_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_type
                    ON artifacts(artifact_type);
            """)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def start_session(self, session_id: str, label: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, label, created_at) VALUES (?, ?, ?)",
                (session_id, label, time.time()),
            )

    def record_artifact(
        self,
        session_id: str,
        artifact_type: str,
        text_content: str,
        source_chunk_ids: list[str],
        metadata: dict | None = None,
    ) -> int:
        with self._conn() as conn:
            # implicit session creation
            conn.execute(
                "INSERT OR IGNORE INTO sessions"
                " (session_id, label, created_at) VALUES (?, NULL, ?)",
                (session_id, time.time()),
            )
            cur = conn.execute(
                """INSERT INTO artifacts
                   (session_id, artifact_type, text_content,
                    source_chunk_ids, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    artifact_type,
                    text_content,
                    json.dumps(source_chunk_ids),
                    json.dumps(metadata or {}),
                    time.time(),
                ),
            )
            return int(cur.lastrowid)  # type: ignore[arg-type]

    def get_chunk_retrieval_counts(self, chunk_ids: list[str]) -> dict[str, int]:
        """Return how many query_memory artifacts have previously retrieved each chunk."""
        if not chunk_ids:
            return {}
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT source_chunk_ids FROM artifacts WHERE artifact_type = 'query_memory'"
            ).fetchall()
        counts: dict[str, int] = {cid: 0 for cid in chunk_ids}
        chunk_set = set(chunk_ids)
        for row in rows:
            try:
                ids: list[str] = json.loads(row["source_chunk_ids"])
            except (json.JSONDecodeError, TypeError):
                continue
            for cid in ids:
                if cid in chunk_set:
                    counts[cid] = counts.get(cid, 0) + 1
        return counts

    def get_session_artifacts(self, session_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def export_for_consolidation(self, since: datetime | None = None) -> list[dict]:
        since_ts = since.timestamp() if since else 0.0
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE created_at > ? ORDER BY created_at",
                (since_ts,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def close(self) -> None:
        pass  # per-method connections — idempotent no-op


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "artifact_type": row["artifact_type"],
        "text_content": row["text_content"],
        "source_chunk_ids": json.loads(row["source_chunk_ids"]),
        "metadata": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
    }
