"""SQLite trajectory store: one replayable row per model attempt.

Every row carries the full task input and raw output, so any request can be
replayed and re-verified later. audit_* columns hold Layer 3 sampled offline
audit results; they stay NULL/0 for rows the audit did not sample.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Union

from .models import TrajectoryRow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trajectory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    category TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('local', 'remote')),
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    verifier_passed INTEGER NOT NULL,
    verifier_failures TEXT NOT NULL,       -- JSON array of check IDs
    escalated INTEGER NOT NULL DEFAULT 0,
    latency_ms REAL NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    task_input TEXT NOT NULL DEFAULT '',
    raw_text TEXT NOT NULL DEFAULT '',
    audit_sampled INTEGER NOT NULL DEFAULT 0,
    audit_result TEXT,                     -- 'pass' | 'fail' | NULL
    audit_violations TEXT                  -- JSON array (Layer 3), NULL if unsampled
);
CREATE INDEX IF NOT EXISTS idx_trajectory_category ON trajectory (category);
CREATE INDEX IF NOT EXISTS idx_trajectory_request ON trajectory (request_id);
"""


class TrajectoryStore:
    def __init__(self, path: Union[str, Path] = ":memory:"):
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, row: TrajectoryRow) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO trajectory (
                request_id, ts, category, contract_id, contract_version,
                tier, provider, model_id, verifier_passed, verifier_failures,
                escalated, latency_ms, cost_usd, prompt_tokens, completion_tokens,
                task_input, raw_text, audit_sampled, audit_result, audit_violations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.request_id,
                row.ts.isoformat(),
                row.category,
                row.contract_id,
                row.contract_version,
                row.tier,
                row.provider,
                row.model_id,
                int(row.verifier_passed),
                json.dumps(row.verifier_failures),
                int(row.escalated),
                row.latency_ms,
                row.cost_usd,
                row.prompt_tokens,
                row.completion_tokens,
                row.task_input,
                row.raw_text,
                int(row.audit_sampled),
                row.audit_result,
                json.dumps(row.audit_violations)
                if row.audit_violations is not None
                else None,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def _to_row(self, r: sqlite3.Row) -> TrajectoryRow:
        return TrajectoryRow(
            db_id=r["id"],
            request_id=r["request_id"],
            ts=datetime.fromisoformat(r["ts"]),
            category=r["category"],
            contract_id=r["contract_id"],
            contract_version=r["contract_version"],
            tier=r["tier"],
            provider=r["provider"],
            model_id=r["model_id"],
            verifier_passed=bool(r["verifier_passed"]),
            verifier_failures=json.loads(r["verifier_failures"]),
            escalated=bool(r["escalated"]),
            latency_ms=r["latency_ms"],
            cost_usd=r["cost_usd"],
            prompt_tokens=r["prompt_tokens"],
            completion_tokens=r["completion_tokens"],
            task_input=r["task_input"],
            raw_text=r["raw_text"],
            audit_sampled=bool(r["audit_sampled"]),
            audit_result=r["audit_result"],
            audit_violations=json.loads(r["audit_violations"])
            if r["audit_violations"] is not None
            else None,
        )

    def rows_for_request(self, request_id: str) -> list[TrajectoryRow]:
        rows = self._conn.execute(
            "SELECT * FROM trajectory WHERE request_id = ? ORDER BY id", (request_id,)
        ).fetchall()
        return [self._to_row(r) for r in rows]

    def rows_for_category(
        self, category: str, limit: int = 100
    ) -> list[TrajectoryRow]:
        rows = self._conn.execute(
            "SELECT * FROM trajectory WHERE category = ? ORDER BY id DESC LIMIT ?",
            (category, limit),
        ).fetchall()
        return [self._to_row(r) for r in rows]

    def update_audit(
        self,
        db_id: int,
        audit_result: str,
        audit_violations: list[dict],
    ) -> None:
        """Narrow audit-field update by row identity; touches nothing else."""
        self._conn.execute(
            "UPDATE trajectory SET audit_sampled = 1, audit_result = ?, "
            "audit_violations = ? WHERE id = ?",
            (audit_result, json.dumps(audit_violations), db_id),
        )
        self._conn.commit()

    def all_rows(self) -> list[TrajectoryRow]:
        rows = self._conn.execute("SELECT * FROM trajectory ORDER BY id").fetchall()
        return [self._to_row(r) for r in rows]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM trajectory").fetchone()[0])

    def close(self) -> None:
        self._conn.close()
