from __future__ import annotations

import re
from typing import Any


def extract_runtime_notes(output: str, tool_events: list[dict[str, Any]] | None = None) -> dict[str, str]:
    notes: dict[str, str] = {}
    text = output or ""

    foothold_patterns = [
        r"\bwww-data\b.*\bshell\b",
        r"\broot\b.*\bshell\b",
        r"\buid=\d+\b.*",
        r"\bAdministrator\b.*",
    ]
    for pattern in foothold_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            notes["foothold"] = match.group(0)[:500]
            break

    credential_patterns = [
        r"password\s*[:=]\s*([^\s]+)",
        r"token\s*[:=]\s*([^\s]+)",
        r"flag\{[^}\n]+\}",
    ]
    for pattern in credential_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            notes["credential_hint"] = match.group(0)[:500]
            break

    if tool_events:
        notes["last_tool_count"] = str(len(tool_events))

    if text:
        notes["last_summary"] = text[:1000]
    return notes


def should_view_hint(
    failure_count: int,
    challenge_hint_viewed: bool,
    notes: dict[str, str] | None = None,
    seconds_since_progress: float | None = None,
) -> bool:
    notes = notes or {}
    if challenge_hint_viewed:
        return False
    if notes.get("hint_viewed") == "true":
        return False
    if failure_count < 3:
        return False
    if seconds_since_progress is None:
        return False
    return seconds_since_progress >= 300
