from __future__ import annotations

import re
from typing import Any

from niuniu_agent.control_plane.challenge_store import sanitize_flag_record_for_prompt


TRACK3_CHALLENGE_CODES = (
    "6RmRST2HkeTbwgbyMJaN",
    "K7kbx40FbhQNODZkS",
    "2ihdUTWqg7iVcvvD7GAZzOadCxS",
)

STALE_MEMORY_TYPES = {
    "persistent_last_summary",
    "persistent_provisional_findings",
    "turn_summary",
    "operator_strategy",
    "persistent_credential_hint",
    "credential_hint",
    "foothold",
    "deferred",
}

STALE_NOTE_KEYS = {
    "provisional_findings",
    "last_summary",
    "foothold",
    "credential_hint",
    "shared_findings",
    "target_unreachable",
    "last_error",
    "deprioritized_reason",
    "instance_drift_warning",
}

STALE_PATTERNS = (
    re.compile(r"\b10\.0\.163\.\d{1,3}(?::\d+)?\b"),
    re.compile(r"\b(?:172\.18|172\.19|172\.20|192\.168)\.\d{1,3}\.\d{1,3}(?::\d+)?\b"),
    re.compile(r"/(?:uploads|backup)/[A-Za-z0-9._-]+\.(?:php|jsp|aspx|ashx)\b"),
    re.compile(r"(?:^|/)(?:lv|pp|suo5|b|c|cv9v9nr)\.php\b"),
)


def _contains_stale_marker(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in STALE_PATTERNS)


def cleanup_track3_stale_memory(state_store: Any) -> dict[str, object]:
    summary: dict[str, object] = {
        "challenge_codes": list(TRACK3_CHALLENGE_CODES),
        "deleted_memories": 0,
        "deleted_notes": 0,
        "sanitized_flag_records": 0,
        "per_challenge": {},
    }
    with state_store._connect() as connection:  # noqa: SLF001
        for code in TRACK3_CHALLENGE_CODES:
            per = {
                "deleted_memories": 0,
                "deleted_notes": 0,
                "sanitized_flag_records": 0,
            }

            note_rows = connection.execute(
                """
                SELECT note_key, note_value
                FROM challenge_notes
                WHERE challenge_code = ?
                """,
                (code,),
            ).fetchall()
            for note_key, note_value in note_rows:
                if note_key not in STALE_NOTE_KEYS:
                    continue
                if not _contains_stale_marker(str(note_value or "")):
                    continue
                connection.execute(
                    """
                    DELETE FROM challenge_notes
                    WHERE challenge_code = ? AND note_key = ?
                    """,
                    (code, note_key),
                )
                per["deleted_notes"] += 1
                summary["deleted_notes"] += 1

            memory_rows = connection.execute(
                """
                SELECT id, memory_type, content
                FROM challenge_memories
                WHERE challenge_code = ?
                """,
                (code,),
            ).fetchall()
            for memory_id, memory_type, content in memory_rows:
                text = str(content or "")
                if memory_type == "persistent_hint":
                    continue
                if memory_type == "persistent_flag_record":
                    sanitized = sanitize_flag_record_for_prompt(text)
                    if sanitized and sanitized != text:
                        connection.execute(
                            """
                            UPDATE challenge_memories
                            SET content = ?
                            WHERE id = ?
                            """,
                            (sanitized, memory_id),
                        )
                        per["sanitized_flag_records"] += 1
                        summary["sanitized_flag_records"] += 1
                    continue
                if memory_type not in STALE_MEMORY_TYPES:
                    continue
                if not _contains_stale_marker(text):
                    continue
                connection.execute(
                    """
                    DELETE FROM challenge_memories
                    WHERE id = ?
                    """,
                    (memory_id,),
                )
                per["deleted_memories"] += 1
                summary["deleted_memories"] += 1

            summary["per_challenge"][code] = per
    return summary
