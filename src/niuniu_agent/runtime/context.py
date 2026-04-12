from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from niuniu_agent.config import AgentSettings


@dataclass(slots=True)
class RuntimeContext:
    settings: AgentSettings
    contest_gateway: Any
    challenge_store: Any
    state_store: Any
    event_logger: Any
    local_toolbox: Any
    skill_registry: Any | None = None
    provider_router: Any | None = None
    agent_id: str | None = None
    agent_role: str | None = None
    challenge_code: str | None = None
    notes: dict[str, Any] = field(default_factory=dict)

    def spawn(
        self,
        *,
        agent_id: str | None = None,
        agent_role: str | None = None,
        challenge_code: str | None = None,
    ) -> "RuntimeContext":
        return RuntimeContext(
            settings=self.settings,
            contest_gateway=self.contest_gateway,
            challenge_store=self.challenge_store,
            state_store=self.state_store,
            event_logger=self.event_logger,
            local_toolbox=self.local_toolbox,
            skill_registry=self.skill_registry,
            provider_router=self.provider_router,
            agent_id=agent_id,
            agent_role=agent_role,
            challenge_code=challenge_code,
            notes={},
        )
