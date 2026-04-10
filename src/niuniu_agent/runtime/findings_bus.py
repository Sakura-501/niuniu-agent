from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class Finding:
    challenge_code: str
    source: str
    content: str
    timestamp: float = field(default_factory=time.time)


class ChallengeFindingsBus:
    def __init__(self) -> None:
        self._findings: list[Finding] = []
        self._cursors: dict[tuple[str, str], int] = {}
        self._lock = asyncio.Lock()

    async def post(self, challenge_code: str, source: str, content: str) -> None:
        async with self._lock:
            self._findings.append(Finding(challenge_code=challenge_code, source=source, content=content))
            if len(self._findings) > 200:
                trim = len(self._findings) - 200
                self._findings = self._findings[trim:]
                self._cursors = {key: max(0, value - trim) for key, value in self._cursors.items()}

    async def check(self, challenge_code: str, consumer: str) -> list[Finding]:
        async with self._lock:
            cursor_key = (challenge_code, consumer)
            cursor = self._cursors.get(cursor_key, 0)
            unread = [
                finding
                for finding in self._findings[cursor:]
                if finding.challenge_code == challenge_code and finding.source != consumer
            ]
            self._cursors[cursor_key] = len(self._findings)
            return unread

    @staticmethod
    def format_unread(findings: list[Finding]) -> str:
        if not findings:
            return ""
        parts = [f"[{finding.source}] {finding.content}" for finding in findings]
        return "Shared findings:\n" + "\n".join(parts)
