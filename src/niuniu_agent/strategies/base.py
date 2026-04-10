from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackStrategy:
    track_id: str
    name: str
    system_prompt: str
    max_iterations: int = 12
