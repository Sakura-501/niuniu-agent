from __future__ import annotations

from dataclasses import dataclass

from niuniu_agent.models import Challenge
from niuniu_agent.strategies.base import TrackStrategy
from niuniu_agent.strategies.track1 import STRATEGY as TRACK1
from niuniu_agent.strategies.track2 import STRATEGY as TRACK2
from niuniu_agent.strategies.track3 import STRATEGY as TRACK3
from niuniu_agent.strategies.track4 import STRATEGY as TRACK4


@dataclass(slots=True)
class StrategyRouter:
    strategies: dict[str, TrackStrategy]

    KEYWORDS = (
        ("track2", ("web", "portal", "admin", "login", "后台", "网站")),
        ("track3", ("api", "graphql", "json", "jwt", "token", "mcp")),
        ("track4", ("binary", "reverse", "crypto", "forensics", "artifact", "misc")),
        ("track1", ("linux", "ubuntu", "shell", "bash", "service", "ssh")),
    )

    LEVEL_MAP = {
        1: "track1",
        2: "track2",
        3: "track3",
        4: "track4",
    }

    @classmethod
    def default(cls) -> "StrategyRouter":
        return cls(
            strategies={
                "track1": TRACK1,
                "track2": TRACK2,
                "track3": TRACK3,
                "track4": TRACK4,
            }
        )

    def route(self, challenge: Challenge) -> TrackStrategy:
        haystack = f"{challenge.title}\n{challenge.description}".lower()
        for track_id, keywords in self.KEYWORDS:
            if any(keyword in haystack for keyword in keywords):
                return self.strategies[track_id]

        track_id = self.LEVEL_MAP.get(challenge.level, "track1")
        return self.strategies[track_id]
