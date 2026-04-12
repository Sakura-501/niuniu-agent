from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

import typer

from niuniu_agent.config import AgentMode, AgentSettings
from niuniu_agent.control_plane import ChallengeStore, ContestGateway
from niuniu_agent.model_routing import ModelProviderRouter
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


@app.command("clear-memory")
def clear_memory(
    runtime_dir: Path = typer.Option(Path("runtime"), "--runtime-dir"),
    yes: bool = typer.Option(False, "--yes", help="Confirm deletion of local runtime memory."),
    include_sessions: bool = typer.Option(True, "--include-sessions/--keep-sessions"),
) -> None:
    if not yes:
        raise typer.BadParameter("pass --yes to clear persisted runtime memory")

    runtime_dir.mkdir(parents=True, exist_ok=True)
    state_store = StateStore(runtime_dir / "state.db")
    cleared = state_store.clear_runtime_memory()
    typer.echo(f"cleared runtime tables: {cleared}")

    if include_sessions:
        session_db = runtime_dir / "sessions.sqlite3"
        if session_db.exists():
            session_db.unlink()
            typer.echo(f"removed session database: {session_db}")


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
    provider_router = ModelProviderRouter(settings, state_store)
    if settings.mode is AgentMode.DEBUG:
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
                provider_router=provider_router,
            )
            event_logger.log("agent.started", {"mode": settings.mode.value, "architecture": "openai-agents"})
            await run_debug_repl(context)
        finally:
            await contest_gateway.cleanup()
        return

    await _run_competition_supervisor(
        settings_kwargs=settings.model_dump(),
        event_logger=event_logger,
        state_store=state_store,
        local_toolbox=local_toolbox,
        skill_registry=skill_registry,
    )


async def _run_competition_supervisor(
    *,
    settings_kwargs: dict[str, Any],
    event_logger: EventLogger,
    state_store: StateStore | None = None,
    local_toolbox: LocalToolbox | None = None,
    skill_registry: SkillRegistry | None = None,
    make_gateway: Callable[[AgentSettings], Any] = ContestGateway.from_settings,
    competition_runner: Callable[[RuntimeContext], Any] = run_competition_loop,
    sleep_fn: Callable[[float], Any] = asyncio.sleep,
) -> None:
    settings = AgentSettings(**settings_kwargs)
    state_store = state_store or StateStore(settings.runtime_dir / "state.db")
    local_toolbox = local_toolbox or LocalToolbox(settings.runtime_dir)
    skill_registry = skill_registry or SkillRegistry()
    provider_router = ModelProviderRouter(settings, state_store)
    backoff = settings.competition_error_backoff_seconds
    attempt = 0

    while True:
        contest_gateway = make_gateway(settings)
        attempt += 1
        try:
            await contest_gateway.connect()
            challenge_store = ChallengeStore(contest_client=contest_gateway, state_store=state_store)
            context = RuntimeContext(
                settings=settings,
                contest_gateway=contest_gateway,
                challenge_store=challenge_store,
                state_store=state_store,
                event_logger=event_logger,
                local_toolbox=local_toolbox,
                skill_registry=skill_registry,
                provider_router=provider_router,
            )
            event_logger.log(
                "agent.started",
                {
                    "mode": settings.mode.value,
                    "architecture": "openai-agents",
                    "supervisor_attempt": attempt,
                },
            )
            await competition_runner(context)
            event_logger.log(
                "competition.supervisor_runner_returned",
                {"attempt": attempt, "backoff_seconds": backoff},
            )
        except asyncio.CancelledError:
            event_logger.log(
                "competition.supervisor_error",
                {
                    "attempt": attempt,
                    "error": "competition runner raised CancelledError; recovering",
                    "backoff_seconds": backoff,
                },
            )
        except Exception as exc:  # pragma: no cover - runtime recovery path
            event_logger.log(
                "competition.supervisor_error",
                {
                    "attempt": attempt,
                    "error": str(exc),
                    "backoff_seconds": backoff,
                },
            )
        finally:
            await contest_gateway.cleanup()

        await sleep_fn(backoff)
        backoff = min(backoff * 2, settings.competition_max_error_backoff_seconds)


def main() -> None:
    app()
