from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from niuniu_agent.config import AgentSettings


@dataclass(slots=True)
class RuntimeContext:
    settings: AgentSettings
    challenge_store: Any
    state_store: Any
    event_logger: Any
    local_toolbox: Any
    notes: dict[str, Any] = field(default_factory=dict)
