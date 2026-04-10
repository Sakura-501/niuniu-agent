from __future__ import annotations

import asyncio

import typer

from niuniu_agent.config import AgentMode, AgentSettings
from niuniu_agent.contest_mcp import ContestMCPClient
from niuniu_agent.controller import AgentController
from niuniu_agent.debug_chat import run_debug_chat
from niuniu_agent.llm import OpenAIToolLoop
from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.router import StrategyRouter
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def callback() -> None:
    """niuniu-agent control plane."""


@app.command()
def run(
    mode: AgentMode | None = typer.Option(None, "--mode"),
    once: bool = typer.Option(False, "--once"),
    challenge_code: str | None = typer.Option(None, "--challenge-code"),
) -> None:
    settings_kwargs = {}
    if mode is not None:
        settings_kwargs["mode"] = mode
    settings = AgentSettings(**settings_kwargs)
    asyncio.run(_run(settings, once=once, challenge_code=challenge_code))


async def _run(settings: AgentSettings, once: bool, challenge_code: str | None) -> None:
    if settings.mode is AgentMode.DEBUG:
        await _run_debug_mode(settings)
        return

    await _run_competition_mode(settings, once=once, challenge_code=challenge_code)


async def _run_debug_mode(settings: AgentSettings) -> None:
    event_logger = EventLogger(settings.runtime_dir / "events.jsonl")
    state_store = StateStore(settings.runtime_dir / "state.db")
    toolbox = LocalToolbox(settings.runtime_dir)
    router = StrategyRouter.default()
    solver = OpenAIToolLoop(
        model=settings.model,
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        max_iterations=settings.llm_max_iterations,
    )

    event_logger.log("agent.started", {"mode": settings.mode.value})
    async with ContestMCPClient(settings.contest_mcp_url, settings.contest_token) as contest_client:
        controller = AgentController(
            settings=settings,
            contest_client=contest_client,
            state_store=state_store,
            event_logger=event_logger,
            router=router,
            toolbox=toolbox,
            solver=solver,
        )
        await run_debug_chat(controller)


async def _run_competition_mode(
    settings: AgentSettings,
    once: bool,
    challenge_code: str | None,
) -> None:
    event_logger = EventLogger(settings.runtime_dir / "events.jsonl")
    state_store = StateStore(settings.runtime_dir / "state.db")
    toolbox = LocalToolbox(settings.runtime_dir)
    router = StrategyRouter.default()
    solver = OpenAIToolLoop(
        model=settings.model,
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        max_iterations=settings.llm_max_iterations,
    )

    event_logger.log("agent.started", {"mode": settings.mode.value})
    async with ContestMCPClient(settings.contest_mcp_url, settings.contest_token) as contest_client:
        controller = AgentController(
            settings=settings,
            contest_client=contest_client,
            state_store=state_store,
            event_logger=event_logger,
            router=router,
            toolbox=toolbox,
            solver=solver,
        )

        while True:
            await controller.run_once(target_challenge_code=challenge_code)
            if once:
                break
            await asyncio.sleep(settings.poll_interval_seconds)


def main() -> None:
    app()
