"""SQLite Layer 2/3 store: interaction events, boosts, relationship edges."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ChunkBoost:
    point_id: str
    hit_count: float
    last_seen_at: str
    ema_score: float
    memory_tier: str
    click_count: float


@dataclass(slots=True)
class RelationshipEdge:
    src_point_id: str
    dst_point_id: str
    score: float
    score_version: str
    created_at: str


class InteractionStore:
    """Local SQLite persistence for interaction memory and dreaming edges."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS interaction_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    point_id TEXT NOT NULL,
                    query_text_hash TEXT,
                    memory_tier TEXT,
                    ts TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_ts ON interaction_events(ts);
                CREATE INDEX IF NOT EXISTS idx_events_point ON interaction_events(point_id);

                CREATE TABLE IF NOT EXISTS chunk_boosts (
                    point_id TEXT PRIMARY KEY,
                    hit_count REAL NOT NULL DEFAULT 0,
                    last_seen_at TEXT NOT NULL,
                    ema_score REAL NOT NULL DEFAULT 0,
                    memory_tier TEXT NOT NULL DEFAULT 'default',
                    click_count REAL NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS relationship_edges (
                    src_point_id TEXT NOT NULL,
                    dst_point_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    score_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (src_point_id, dst_point_id, score_version)
                );
                CREATE INDEX IF NOT EXISTS idx_edges_src ON relationship_edges(src_point_id);
                """
            )

    def record_event(
        self,
        *,
        session_id: str,
        event_type: str,
        point_id: str,
        query_text_hash: str | None,
        memory_tier: str,
        weight: float,
        apply_boost: bool,
        ts: str | None = None,
    ) -> None:
        event_ts = ts or datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO interaction_events
                    (session_id, event_type, point_id, query_text_hash, memory_tier, ts)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, event_type, point_id, query_text_hash, memory_tier, event_ts),
            )
            if apply_boost and weight > 0:
                click_delta = weight if event_type in ("result_click", "result_expand") else 0.0
                row = conn.execute(
                    "SELECT hit_count, ema_score, click_count FROM chunk_boosts WHERE point_id = ?",
                    (point_id,),
                ).fetchone()
                if row is None:
                    ema = weight
                    hit = weight
                    clicks = click_delta
                else:
                    prev_ema = float(row["ema_score"])
                    hit = float(row["hit_count"]) + weight
                    clicks = float(row["click_count"]) + click_delta
                    ema = 0.7 * prev_ema + 0.3 * weight
                conn.execute(
                    """
                    INSERT INTO chunk_boosts
                        (point_id, hit_count, last_seen_at, ema_score, memory_tier, click_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(point_id) DO UPDATE SET
                        hit_count = excluded.hit_count,
                        last_seen_at = excluded.last_seen_at,
                        ema_score = excluded.ema_score,
                        memory_tier = excluded.memory_tier,
                        click_count = excluded.click_count
                    """,
                    (point_id, hit, event_ts, ema, memory_tier, clicks),
                )

    def get_boosts(self, point_ids: list[str]) -> dict[str, ChunkBoost]:
        if not point_ids:
            return {}
        placeholders = ",".join("?" * len(point_ids))
        with self._connect() as conn:
            # placeholders are only "?" tokens sized to len(point_ids); values are bound.
            rows = conn.execute(
                "SELECT point_id, hit_count, last_seen_at, ema_score, memory_tier, click_count "
                "FROM chunk_boosts WHERE point_id IN (" + placeholders + ")",  # nosec B608
                point_ids,
            ).fetchall()
        return {
            str(row["point_id"]): ChunkBoost(
                point_id=str(row["point_id"]),
                hit_count=float(row["hit_count"]),
                last_seen_at=str(row["last_seen_at"]),
                ema_score=float(row["ema_score"]),
                memory_tier=str(row["memory_tier"]),
                click_count=float(row["click_count"]),
            )
            for row in rows
        }

    def max_hit_count(self) -> float:
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(hit_count) AS m FROM chunk_boosts").fetchone()
        value = row["m"] if row is not None else None
        return float(value) if value is not None else 0.0

    def list_boosted_points(self, *, limit: int = 64) -> list[ChunkBoost]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT point_id, hit_count, last_seen_at, ema_score, memory_tier, click_count
                FROM chunk_boosts
                ORDER BY hit_count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            ChunkBoost(
                point_id=str(row["point_id"]),
                hit_count=float(row["hit_count"]),
                last_seen_at=str(row["last_seen_at"]),
                ema_score=float(row["ema_score"]),
                memory_tier=str(row["memory_tier"]),
                click_count=float(row["click_count"]),
            )
            for row in rows
        ]

    def seconds_since_last_event(self) -> float | None:
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(ts) AS latest FROM interaction_events").fetchone()
        latest = row["latest"] if row is not None else None
        if not latest:
            return None
        try:
            parsed = datetime.fromisoformat(str(latest))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return max(0.0, (datetime.now(UTC) - parsed).total_seconds())
        except ValueError:
            return None

    def upsert_edges(self, edges: list[RelationshipEdge]) -> int:
        if not edges:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO relationship_edges
                    (src_point_id, dst_point_id, score, score_version, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(src_point_id, dst_point_id, score_version) DO UPDATE SET
                    score = excluded.score,
                    created_at = excluded.created_at
                """,
                [
                    (
                        edge.src_point_id,
                        edge.dst_point_id,
                        edge.score,
                        edge.score_version,
                        edge.created_at,
                    )
                    for edge in edges
                ],
            )
        return len(edges)

    def edges_for_points(
        self, point_ids: list[str], *, score_version: str | None = None, limit: int = 50
    ) -> list[RelationshipEdge]:
        if not point_ids:
            return []
        placeholders = ",".join("?" * len(point_ids))
        params: list[Any] = list(point_ids) + list(point_ids)
        # Bound parameters only; IN list is a fixed count of "?" placeholders.
        sql = (
            "SELECT src_point_id, dst_point_id, score, score_version, created_at "
            "FROM relationship_edges WHERE (src_point_id IN ("
            + placeholders  # nosec B608
            + ") OR dst_point_id IN ("
            + placeholders  # nosec B608
            + "))"
        )
        if score_version:
            sql += " AND score_version = ?"
            params.append(score_version)
        sql += " ORDER BY score DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            RelationshipEdge(
                src_point_id=str(row["src_point_id"]),
                dst_point_id=str(row["dst_point_id"]),
                score=float(row["score"]),
                score_version=str(row["score_version"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]


def boost_norm(hit_count: float, hit_count_max: float) -> float:
    if hit_count <= 0:
        return 0.0
    denom = math.log1p(max(hit_count_max, hit_count))
    if denom <= 0:
        return 0.0
    return math.log1p(hit_count) / denom
