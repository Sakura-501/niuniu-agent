from __future__ import annotations

import sqlite3
import time
import json
from pathlib import Path


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS submitted_flags (
                    challenge_code TEXT NOT NULL,
                    flag TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (challenge_code, flag)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS challenge_runtime_state (
                    challenge_code TEXT PRIMARY KEY,
                    active INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    last_progress_at REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS challenge_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenge_code TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS challenge_notes (
                    challenge_code TEXT NOT NULL,
                    note_key TEXT NOT NULL,
                    note_value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (challenge_code, note_key)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_status (
                    agent_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    challenge_code TEXT,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    last_error TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    challenge_code TEXT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._migrate_schema(connection)

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        self._ensure_column(
            connection,
            table="challenge_runtime_state",
            column="last_progress_at",
            definition="REAL",
        )

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {row[1] for row in rows}
        if column in existing:
            return
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def record_submitted_flag(self, challenge_code: str, flag: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO submitted_flags (challenge_code, flag)
                VALUES (?, ?)
                """,
                (challenge_code, flag),
            )

    def has_submitted_flag(self, challenge_code: str, flag: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM submitted_flags
                WHERE challenge_code = ? AND flag = ?
                LIMIT 1
                """,
                (challenge_code, flag),
            ).fetchone()
        return row is not None

    def list_submitted_flags(self, challenge_code: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT flag
                FROM submitted_flags
                WHERE challenge_code = ?
                ORDER BY created_at ASC, flag ASC
                """,
                (challenge_code,),
            ).fetchall()
        return [row[0] for row in rows]

    def mark_active_challenge(self, challenge_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (challenge_code, active, failure_count, last_error)
                VALUES (?, 1, 0, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code,),
            )

    def clear_active_challenge(self, challenge_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (challenge_code, active, failure_count, last_error)
                VALUES (?, 0, 0, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 0,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code,),
            )

    def record_challenge_failure(self, challenge_code: str, error: str) -> int:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (challenge_code, active, failure_count, last_error)
                VALUES (?, 1, 1, ?)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 1,
                    failure_count = failure_count + 1,
                    last_error = excluded.last_error,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code, error),
            )
            row = connection.execute(
                """
                SELECT failure_count
                FROM challenge_runtime_state
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            ).fetchone()
        return int(row[0]) if row else 0

    def record_challenge_success(self, challenge_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (challenge_code, active, failure_count, last_error)
                VALUES (?, 0, 0, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 0,
                    failure_count = 0,
                    last_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code,),
            )

    def get_challenge_runtime_state(self, challenge_code: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT active, failure_count, last_error, last_progress_at
                FROM challenge_runtime_state
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            ).fetchone()
        if row is None:
            return {"active": False, "failure_count": 0, "last_error": None, "last_progress_at": None}
        return {
            "active": bool(row[0]),
            "failure_count": int(row[1]),
            "last_error": row[2],
            "last_progress_at": row[3],
        }

    def mark_progress(self, challenge_code: str) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (challenge_code, active, failure_count, last_error, last_progress_at)
                VALUES (?, 1, 0, NULL, ?)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    last_progress_at = excluded.last_progress_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code, now),
            )

    def seconds_since_progress(self, challenge_code: str, now: float | None = None) -> float | None:
        state = self.get_challenge_runtime_state(challenge_code)
        last = state.get("last_progress_at")
        if last in (None, ""):
            return None
        current = time.time() if now is None else now
        return max(0.0, current - float(last))

    def add_history_event(self, challenge_code: str, event_type: str, payload: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_history (challenge_code, event_type, payload)
                VALUES (?, ?, ?)
                """,
                (challenge_code, event_type, payload),
            )

    def list_history(self, challenge_code: str, limit: int = 10) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_type, payload, created_at
                FROM challenge_history
                WHERE challenge_code = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (challenge_code, limit),
            ).fetchall()
        return [
            {"event_type": row[0], "payload": row[1], "created_at": row[2]}
            for row in rows
        ]

    def set_challenge_note(self, challenge_code: str, note_key: str, note_value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_notes (challenge_code, note_key, note_value)
                VALUES (?, ?, ?)
                ON CONFLICT(challenge_code, note_key) DO UPDATE SET
                    note_value = excluded.note_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code, note_key, note_value),
            )

    def get_challenge_notes(self, challenge_code: str) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT note_key, note_value
                FROM challenge_notes
                WHERE challenge_code = ?
                ORDER BY note_key ASC
                """,
                (challenge_code,),
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def upsert_agent_status(
        self,
        agent_id: str,
        role: str,
        challenge_code: str | None,
        status: str,
        summary: str = "",
        metadata: dict[str, object] | None = None,
        last_error: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_status (agent_id, role, challenge_code, status, summary, metadata, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    role = excluded.role,
                    challenge_code = excluded.challenge_code,
                    status = excluded.status,
                    summary = excluded.summary,
                    metadata = excluded.metadata,
                    last_error = excluded.last_error,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    agent_id,
                    role,
                    challenge_code,
                    status,
                    summary,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    last_error,
                ),
            )

    def get_agent_status(self, agent_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT agent_id, role, challenge_code, status, summary, metadata, last_error, updated_at
                FROM agent_status
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "agent_id": row[0],
            "role": row[1],
            "challenge_code": row[2],
            "status": row[3],
            "summary": row[4],
            "metadata": self._load_json_dict(row[5]),
            "last_error": row[6],
            "updated_at": row[7],
        }

    def list_agent_statuses(
        self,
        *,
        role: str | None = None,
        challenge_code: str | None = None,
    ) -> list[dict[str, object]]:
        query = (
            "SELECT agent_id, role, challenge_code, status, summary, metadata, last_error, updated_at "
            "FROM agent_status"
        )
        clauses: list[str] = []
        params: list[object] = []
        if role is not None:
            clauses.append("role = ?")
            params.append(role)
        if challenge_code is not None:
            clauses.append("challenge_code = ?")
            params.append(challenge_code)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, agent_id ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "agent_id": row[0],
                "role": row[1],
                "challenge_code": row[2],
                "status": row[3],
                "summary": row[4],
                "metadata": self._load_json_dict(row[5]),
                "last_error": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]

    def append_agent_event(
        self,
        *,
        agent_id: str,
        challenge_code: str | None,
        event_type: str,
        payload: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_events (agent_id, challenge_code, event_type, payload)
                VALUES (?, ?, ?, ?)
                """,
                (agent_id, challenge_code, event_type, payload),
            )

    def list_agent_events(
        self,
        *,
        agent_id: str | None = None,
        challenge_code: str | None = None,
        limit: int = 100,
        ascending: bool = False,
    ) -> list[dict[str, object]]:
        query = (
            "SELECT agent_id, challenge_code, event_type, payload, created_at "
            "FROM agent_events"
        )
        clauses: list[str] = []
        params: list[object] = []
        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if challenge_code is not None:
            clauses.append("challenge_code = ?")
            params.append(challenge_code)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id " + ("ASC" if ascending else "DESC") + " LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "agent_id": row[0],
                "challenge_code": row[1],
                "event_type": row[2],
                "payload": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    def delete_agent(self, agent_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM agent_events
                WHERE agent_id = ?
                """,
                (agent_id,),
            )
            connection.execute(
                """
                DELETE FROM agent_status
                WHERE agent_id = ?
                """,
                (agent_id,),
            )

    @staticmethod
    def _load_json_dict(raw: str | None) -> dict[str, object]:
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
