from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ChallengeSnapshot:
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

    @property
    def completed(self) -> bool:
        if self.flag_count > 0:
            return self.flag_got_count >= self.flag_count
        if self.total_score > 0:
            return self.total_got_score >= self.total_score
        return False


@dataclass(slots=True)
class ContestSnapshot:
    current_level: int | None
    total_challenges: int
    solved_challenges: int | None
    challenges: list[ChallengeSnapshot]
