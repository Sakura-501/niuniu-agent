from __future__ import annotations

import asyncio

import typer

from niuniu_agent.config import AgentMode, AgentSettings
from niuniu_agent.control_plane import ChallengeStore, ContestGateway
from niuniu_agent.runtime.competition_loop import run_competition_loop
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.debug_repl import run_debug_repl
from niuniu_agent.skills import SkillRegistry
from niuniu_agent.state_store import StateStore
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def callback() -> None:
    """niuniu-agent rebuilt with openai-agents."""


@app.command()
def run(
    mode: AgentMode | None = typer.Option(None, "--mode"),
) -> None:
    settings_kwargs = {}
    if mode is not None:
        settings_kwargs["mode"] = mode
    settings = AgentSettings(**settings_kwargs)
    asyncio.run(_run(settings))


async def _run(settings: AgentSettings) -> None:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    event_logger = EventLogger(settings.runtime_dir / "events.jsonl")
    state_store = StateStore(settings.runtime_dir / "state.db")
    local_toolbox = LocalToolbox(settings.runtime_dir)
    inventory = await local_toolbox.check_tool_inventory()
    missing_tools = [tool for tool in inventory["tools"] if not tool["available"]]
    event_logger.log(
        "tool_inventory.checked",
        {"missing_tools": missing_tools, "tool_count": len(inventory["tools"])},
    )
    skill_registry = SkillRegistry()
    contest_gateway = ContestGateway.from_settings(settings)

    await contest_gateway.connect()
    try:
        challenge_store = ChallengeStore(contest_client=contest_gateway, state_store=state_store)
        context = RuntimeContext(
            settings=settings,
            contest_gateway=contest_gateway,
            challenge_store=challenge_store,
            state_store=state_store,
            event_logger=event_logger,
            local_toolbox=local_toolbox,
            skill_registry=skill_registry,
        )
        event_logger.log("agent.started", {"mode": settings.mode.value, "architecture": "openai-agents"})

        if settings.mode is AgentMode.DEBUG:
            await run_debug_repl(context)
        else:
            await run_competition_loop(context)
    finally:
        await contest_gateway.cleanup()


def main() -> None:
    app()
