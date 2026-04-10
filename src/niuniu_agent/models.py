from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Challenge:
    code: str
    title: str
    description: str
    difficulty: str
    level: int
    total_score: int = 0
    total_got_score: int = 0
    flag_count: int = 0
    flag_got_count: int = 0
    hint_viewed: bool = False
    instance_status: str = "stopped"
    entrypoints: list[str] = field(default_factory=list)
