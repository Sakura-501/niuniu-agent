from __future__ import annotations

import asyncio

import typer

from niuniu_agent.config import AgentMode, AgentSettings
from niuniu_agent.contest_mcp import ContestMCPClient
from niuniu_agent.control_plane import ChallengeStore
from niuniu_agent.runtime.competition_loop import run_competition_loop
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.debug_repl import run_debug_repl
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

    async with ContestMCPClient(settings.contest_mcp_url, settings.contest_token) as contest_client:
        challenge_store = ChallengeStore(contest_client=contest_client, state_store=state_store)
        context = RuntimeContext(
            settings=settings,
            challenge_store=challenge_store,
            state_store=state_store,
            event_logger=event_logger,
            local_toolbox=local_toolbox,
        )
        event_logger.log("agent.started", {"mode": settings.mode.value, "architecture": "openai-agents"})

        if settings.mode is AgentMode.DEBUG:
            await run_debug_repl(context)
        else:
            await run_competition_loop(context)


def main() -> None:
    app()
