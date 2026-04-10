from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Challenge:
    code: str
    title: str
    description: str
    difficulty: str
    level: int
    instance_status: str = "stopped"
    entrypoints: list[str] = field(default_factory=list)
