from __future__ import annotations

from dataclasses import dataclass

from agents import Agent, ModelSettings
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

from niuniu_agent.agent_stack.model import build_chat_completions_model
from niuniu_agent.agent_stack.tools import build_local_tools
from niuniu_agent.config import AgentSettings


@dataclass(slots=True)
class AgentAssembly:
    manager: Agent
    specialists: dict[str, Agent]
    contest_server: MCPServerStreamableHttp


def _specialist(name: str, instructions: str, settings: AgentSettings) -> Agent:
    return Agent(
        name=name,
        handoff_description=f"Specialist for {name}",
        instructions=instructions,
        model=build_chat_completions_model(settings),
        model_settings=ModelSettings(max_tokens=4000, parallel_tool_calls=False),
    )


def build_agent_assembly(settings: AgentSettings) -> AgentAssembly:
    contest_server = MCPServerStreamableHttp(
        params=MCPServerStreamableHttpParams(
            url=settings.contest_mcp_url,
            headers={"Authorization": f"Bearer {settings.contest_token}"},
        ),
        name="contest-mcp",
        cache_tools_list=True,
        max_retry_attempts=2,
    )

    specialists = {
        "track1": _specialist(
            "track1_specialist",
            "Focus on Linux service discovery, shell access, file hunting, and privilege clues.",
            settings,
        ),
        "track2": _specialist(
            "track2_specialist",
            "Focus on web attack surface, auth bypass, parameter abuse, and admin functionality.",
            settings,
        ),
        "track3": _specialist(
            "track3_specialist",
            "Focus on APIs, tokens, JSON workflows, authz gaps, and tool-friendly exploitation.",
            settings,
        ),
        "track4": _specialist(
            "track4_specialist",
            "Focus on deeper chained workflows, encoded artifacts, and non-obvious exploitation paths.",
            settings,
        ),
    }

    manager = Agent(
        name="contest-manager",
        instructions=(
            "You are the main autonomous pentest manager. "
            "Always begin by understanding the latest challenge snapshot via tools. "
            "Keep track of which challenges are completed and which are still open. "
            "Use MCP tools and local tools together. "
            "When a challenge clearly matches a track specialist, hand off to that specialist. "
            "If you discover a flag, submit it immediately. "
            "In debug mode, explain what you are doing. "
            "In competition mode, keep moving and do not stop on uncertainty."
        ),
        tools=build_local_tools(),
        mcp_servers=[contest_server],
        handoffs=list(specialists.values()),
        model=build_chat_completions_model(settings),
        model_settings=ModelSettings(max_tokens=6000, parallel_tool_calls=False),
    )

    return AgentAssembly(manager=manager, specialists=specialists, contest_server=contest_server)
