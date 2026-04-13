from __future__ import annotations

import sqlite3
import time
import json
from datetime import UTC, datetime
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
                    attempt_started_at REAL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    defer_until REAL,
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
                CREATE TABLE IF NOT EXISTS challenge_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenge_code TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (challenge_code, memory_type, content, source)
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_options (
                    option_key TEXT PRIMARY KEY,
                    option_value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_provider_state (
                    provider_id TEXT PRIMARY KEY,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    total_failures INTEGER NOT NULL DEFAULT 0,
                    total_successes INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    last_failure_at REAL,
                    last_success_at REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        self._ensure_column(
            connection,
            table="challenge_runtime_state",
            column="attempt_started_at",
            definition="REAL",
        )
        self._ensure_column(
            connection,
            table="challenge_runtime_state",
            column="attempt_count",
            definition="INTEGER NOT NULL DEFAULT 0",
        )
        self._ensure_column(
            connection,
            table="challenge_runtime_state",
            column="defer_until",
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

    def latest_submitted_flag_at(self, challenge_code: str) -> float | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT created_at
                FROM submitted_flags
                WHERE challenge_code = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (challenge_code,),
            ).fetchone()
        return self._parse_db_timestamp(row[0]) if row and row[0] else None

    def clear_submitted_flags(self, challenge_code: str) -> int:
        with self._connect() as connection:
            count_row = connection.execute(
                """
                SELECT COUNT(*)
                FROM submitted_flags
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            ).fetchone()
            connection.execute(
                """
                DELETE FROM submitted_flags
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            )
        return int(count_row[0] if count_row else 0)

    def latest_submitted_flag_at(self, challenge_code: str) -> float | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT created_at
                FROM submitted_flags
                WHERE challenge_code = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (challenge_code,),
            ).fetchone()
        return self._parse_db_timestamp(row[0]) if row and row[0] else None

    def clear_submitted_flags(self, challenge_code: str) -> int:
        with self._connect() as connection:
            count_row = connection.execute(
                """
                SELECT COUNT(*)
                FROM submitted_flags
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            ).fetchone()
            connection.execute(
                """
                DELETE FROM submitted_flags
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            )
        return int(count_row[0] if count_row else 0)

    def mark_active_challenge(self, challenge_code: str) -> None:
        now = time.time()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT active, attempt_count, attempt_started_at
                FROM challenge_runtime_state
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO challenge_runtime_state (
                        challenge_code, active, failure_count, last_error,
                        attempt_started_at, attempt_count, defer_until
                    )
                    VALUES (?, 1, 0, NULL, ?, 1, NULL)
                    """,
                    (challenge_code, now),
                )
                return
            active = bool(row[0])
            attempt_count = int(row[1] or 0)
            attempt_started_at = row[2]
            if active and attempt_started_at is not None:
                next_started_at = attempt_started_at
                next_attempt_count = attempt_count
            else:
                next_started_at = now
                next_attempt_count = attempt_count + 1
            connection.execute(
                """
                UPDATE challenge_runtime_state
                SET active = 1,
                    attempt_started_at = ?,
                    attempt_count = ?,
                    defer_until = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE challenge_code = ?
                """,
                (next_started_at, next_attempt_count, challenge_code),
            )

    def clear_active_challenge(self, challenge_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (
                    challenge_code, active, failure_count, last_error, attempt_started_at
                )
                VALUES (?, 0, 0, NULL, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 0,
                    attempt_started_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code,),
            )

    def record_challenge_failure(self, challenge_code: str, error: str) -> int:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (
                    challenge_code, active, failure_count, last_error, attempt_started_at
                )
                VALUES (?, 0, 1, ?, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 0,
                    failure_count = failure_count + 1,
                    last_error = excluded.last_error,
                    attempt_started_at = NULL,
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
                INSERT INTO challenge_runtime_state (
                    challenge_code, active, failure_count, last_error, attempt_started_at, defer_until
                )
                VALUES (?, 0, 0, NULL, NULL, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 0,
                    failure_count = 0,
                    last_error = NULL,
                    attempt_started_at = NULL,
                    defer_until = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code,),
            )

    def record_challenge_turn_success(self, challenge_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (
                    challenge_code, active, failure_count, last_error
                )
                VALUES (?, 1, 0, NULL)
                ON CONFLICT(challenge_code) DO UPDATE SET
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
                SELECT active, failure_count, last_error, last_progress_at, attempt_started_at, attempt_count, defer_until
                FROM challenge_runtime_state
                WHERE challenge_code = ?
                """,
                (challenge_code,),
            ).fetchone()
        if row is None:
            return {
                "active": False,
                "failure_count": 0,
                "last_error": None,
                "last_progress_at": None,
                "attempt_started_at": None,
                "attempt_count": 0,
                "defer_until": None,
            }
        return {
            "active": bool(row[0]),
            "failure_count": int(row[1]),
            "last_error": row[2],
            "last_progress_at": row[3],
            "attempt_started_at": row[4],
            "attempt_count": int(row[5] or 0),
            "defer_until": row[6],
        }

    def mark_progress(self, challenge_code: str) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (
                    challenge_code, active, failure_count, last_error, last_progress_at, attempt_started_at, attempt_count
                )
                VALUES (?, 1, 0, NULL, ?, ?, 1)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    last_progress_at = excluded.last_progress_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code, now, now),
            )

    def seconds_since_progress(self, challenge_code: str, now: float | None = None) -> float | None:
        state = self.get_challenge_runtime_state(challenge_code)
        last = state.get("last_progress_at")
        if last in (None, ""):
            return None
        current = time.time() if now is None else now
        return max(0.0, current - float(last))

    def seconds_since_attempt_started(self, challenge_code: str, now: float | None = None) -> float | None:
        state = self.get_challenge_runtime_state(challenge_code)
        started = state.get("attempt_started_at")
        if started in (None, ""):
            return None
        current = time.time() if now is None else now
        return max(0.0, current - float(started))

    def defer_challenge(
        self,
        challenge_code: str,
        *,
        defer_seconds: float,
        reason: str,
        now: float | None = None,
    ) -> None:
        current = time.time() if now is None else now
        defer_until = current + defer_seconds
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO challenge_runtime_state (
                    challenge_code, active, failure_count, last_error, attempt_started_at, defer_until
                )
                VALUES (?, 0, 0, ?, NULL, ?)
                ON CONFLICT(challenge_code) DO UPDATE SET
                    active = 0,
                    last_error = excluded.last_error,
                    attempt_started_at = NULL,
                    defer_until = excluded.defer_until,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (challenge_code, reason, defer_until),
            )

    def is_challenge_deferred(self, challenge_code: str, now: float | None = None) -> bool:
        state = self.get_challenge_runtime_state(challenge_code)
        defer_until = state.get("defer_until")
        if defer_until in (None, ""):
            return False
        current = time.time() if now is None else now
        return float(defer_until) > current

    def seconds_until_dispatchable(self, challenge_code: str, now: float | None = None) -> float | None:
        state = self.get_challenge_runtime_state(challenge_code)
        defer_until = state.get("defer_until")
        if defer_until in (None, ""):
            return None
        current = time.time() if now is None else now
        remaining = float(defer_until) - current
        return remaining if remaining > 0 else 0.0

    def list_active_challenge_codes(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT challenge_code
                FROM challenge_runtime_state
                WHERE active = 1
                ORDER BY challenge_code ASC
                """
            ).fetchall()
        return [str(row[0]) for row in rows if row and row[0]]

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

    def add_challenge_memory(
        self,
        challenge_code: str,
        memory_type: str,
        content: str,
        *,
        source: str = "system",
    ) -> None:
        normalized = content.strip()
        if not normalized:
            return
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO challenge_memories (challenge_code, memory_type, content, source)
                VALUES (?, ?, ?, ?)
                """,
                (challenge_code, memory_type, normalized[:4000], source),
            )

    def list_challenge_memories(self, challenge_code: str, limit: int = 10) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT memory_type, content, source, created_at
                FROM challenge_memories
                WHERE challenge_code = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (challenge_code, limit),
            ).fetchall()
        return [
            {
                "memory_type": row[0],
                "content": row[1],
                "source": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

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

    def set_runtime_option(self, option_key: str, option_value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runtime_options (option_key, option_value)
                VALUES (?, ?)
                ON CONFLICT(option_key) DO UPDATE SET
                    option_value = excluded.option_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (option_key, option_value),
            )

    def delete_runtime_option(self, option_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM runtime_options
                WHERE option_key = ?
                """,
                (option_key,),
            )

    def get_runtime_option(self, option_key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT option_value
                FROM runtime_options
                WHERE option_key = ?
                """,
                (option_key,),
            ).fetchone()
        return row[0] if row else None

    def record_model_provider_failure(self, provider_id: str, error: str, *, now: float | None = None) -> None:
        failure_time = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO model_provider_state (
                    provider_id, consecutive_failures, total_failures, total_successes,
                    last_error, last_failure_at, last_success_at
                )
                VALUES (?, 1, 1, 0, ?, ?, NULL)
                ON CONFLICT(provider_id) DO UPDATE SET
                    consecutive_failures = consecutive_failures + 1,
                    total_failures = total_failures + 1,
                    last_error = excluded.last_error,
                    last_failure_at = excluded.last_failure_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (provider_id, error[:2000], failure_time),
            )

    def record_model_provider_success(self, provider_id: str, *, now: float | None = None) -> None:
        success_time = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO model_provider_state (
                    provider_id, consecutive_failures, total_failures, total_successes,
                    last_error, last_failure_at, last_success_at
                )
                VALUES (?, 0, 0, 1, NULL, NULL, ?)
                ON CONFLICT(provider_id) DO UPDATE SET
                    consecutive_failures = 0,
                    total_successes = total_successes + 1,
                    last_error = NULL,
                    last_success_at = excluded.last_success_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (provider_id, success_time),
            )

    def get_model_provider_state(self, provider_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT consecutive_failures, total_failures, total_successes, last_error, last_failure_at, last_success_at
                FROM model_provider_state
                WHERE provider_id = ?
                """,
                (provider_id,),
            ).fetchone()
        if row is None:
            return {
                "provider_id": provider_id,
                "consecutive_failures": 0,
                "total_failures": 0,
                "total_successes": 0,
                "last_error": None,
                "last_failure_at": None,
                "last_success_at": None,
            }
        return {
            "provider_id": provider_id,
            "consecutive_failures": int(row[0] or 0),
            "total_failures": int(row[1] or 0),
            "total_successes": int(row[2] or 0),
            "last_error": row[3],
            "last_failure_at": row[4],
            "last_success_at": row[5],
        }

    def list_model_provider_states(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT provider_id, consecutive_failures, total_failures, total_successes, last_error, last_failure_at, last_success_at
                FROM model_provider_state
                ORDER BY provider_id ASC
                """
            ).fetchall()
        return [
            {
                "provider_id": row[0],
                "consecutive_failures": int(row[1] or 0),
                "total_failures": int(row[2] or 0),
                "total_successes": int(row[3] or 0),
                "last_error": row[4],
                "last_failure_at": row[5],
                "last_success_at": row[6],
            }
            for row in rows
        ]

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

    def get_agent_last_activity(self, agent_id: str) -> float | None:
        with self._connect() as connection:
            status_row = connection.execute(
                """
                SELECT updated_at
                FROM agent_status
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
            event_row = connection.execute(
                """
                SELECT created_at
                FROM agent_events
                WHERE agent_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (agent_id,),
            ).fetchone()
        timestamps = [
            self._parse_db_timestamp(status_row[0]) if status_row and status_row[0] else None,
            self._parse_db_timestamp(event_row[0]) if event_row and event_row[0] else None,
        ]
        values = [value for value in timestamps if value is not None]
        return max(values) if values else None

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

    def delete_agent_status(self, agent_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM agent_status
                WHERE agent_id = ?
                """,
                (agent_id,),
            )

    def delete_agent_statuses_for_challenge(
        self,
        challenge_code: str,
        *,
        role: str | None = None,
        exclude_statuses: set[str] | None = None,
    ) -> None:
        query = "DELETE FROM agent_status WHERE challenge_code = ?"
        params: list[object] = [challenge_code]
        if role is not None:
            query += " AND role = ?"
            params.append(role)
        if exclude_statuses:
            placeholders = ", ".join("?" for _ in exclude_statuses)
            query += f" AND status NOT IN ({placeholders})"
            params.extend(sorted(exclude_statuses))
        with self._connect() as connection:
            connection.execute(query, tuple(params))

    def clear_runtime_memory(self) -> dict[str, int]:
        tables = (
            "submitted_flags",
            "challenge_runtime_state",
            "challenge_history",
            "challenge_notes",
            "challenge_memories",
            "agent_status",
            "agent_events",
        )
        cleared: dict[str, int] = {}
        with self._connect() as connection:
            for table in tables:
                count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                cleared[table] = int(count[0] if count else 0)
                connection.execute(f"DELETE FROM {table}")
        return cleared

    @staticmethod
    def _load_json_dict(raw: str | None) -> dict[str, object]:
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _parse_db_timestamp(raw: str | None) -> float | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace(" ", "T")).replace(tzinfo=UTC).timestamp()
        except ValueError:
            return None
