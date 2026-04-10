from __future__ import annotations

import sqlite3
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
