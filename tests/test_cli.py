from typer.testing import CliRunner

import asyncio

import pytest

from niuniu_agent.cli import _run_competition_supervisor, app
from niuniu_agent.state_store import StateStore


def test_cli_exposes_run_subcommand() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Commands" in result.stdout
    assert "run" in result.stdout

    run_result = runner.invoke(app, ["run", "--help"])

    assert run_result.exit_code == 0


def test_cli_help_mentions_debug_chat_behavior() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["run", "--help"])

    assert result.exit_code == 0
    assert "--mode" in result.stdout


def test_cli_can_clear_runtime_memory(tmp_path) -> None:
    runner = CliRunner()
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    store = StateStore(runtime_dir / "state.db")
    store.record_submitted_flag("c1", "flag{demo}")
    store.add_history_event("c1", "turn_completed", "summary")
    store.set_challenge_note("c1", "foothold", "user shell")
    session_db = runtime_dir / "sessions.sqlite3"
    session_db.write_text("demo", encoding="utf-8")

    result = runner.invoke(
        app,
        ["clear-memory", "--runtime-dir", str(runtime_dir), "--yes"],
    )

    assert result.exit_code == 0
    assert store.list_submitted_flags("c1") == []
    assert store.list_history("c1") == []
    assert store.get_challenge_notes("c1") == {}
    assert session_db.exists() is False


class DummyGateway:
    def __init__(self) -> None:
        self.connect_calls = 0
        self.cleanup_calls = 0

    async def connect(self) -> None:
        self.connect_calls += 1

    async def cleanup(self) -> None:
        self.cleanup_calls += 1


class DummyLogger:
    def __init__(self) -> None:
        self.events = []

    def log(self, event: str, payload: dict | None = None) -> None:
        self.events.append((event, payload or {}))


class StopSupervisor(Exception):
    pass


@pytest.mark.anyio
async def test_competition_supervisor_restarts_after_runner_error(tmp_path) -> None:
    gateway = DummyGateway()
    logger = DummyLogger()
    attempts = 0
    sleeps = []

    async def runner(context) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("boom")
        asyncio.current_task().cancel()
        await asyncio.sleep(0)

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) >= 2:
            raise StopSupervisor()

    with pytest.raises(StopSupervisor):
        await _run_competition_supervisor(
            settings_kwargs={
                "model": "test-model",
                "model_base_url": "https://example.invalid/v1",
                "model_api_key": "key",
                "contest_host": "https://challenge.zc.tencent.com",
                "contest_token": "token",
                "runtime_dir": tmp_path / "runtime",
            },
            event_logger=logger,
            make_gateway=lambda settings: gateway,
            competition_runner=runner,
            sleep_fn=fake_sleep,
        )

    assert gateway.connect_calls == 2
    assert gateway.cleanup_calls == 2
    assert sleeps == [10, 20]
    assert any(event == "competition.supervisor_error" for event, _ in logger.events)


@pytest.mark.anyio
async def test_competition_supervisor_recovers_from_internal_cancelled_error(tmp_path) -> None:
    gateway = DummyGateway()
    logger = DummyLogger()
    attempts = 0
    sleeps = []

    async def runner(context) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise asyncio.CancelledError()
        asyncio.current_task().cancel()
        await asyncio.sleep(0)

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) >= 2:
            raise StopSupervisor()

    with pytest.raises(StopSupervisor):
        await _run_competition_supervisor(
            settings_kwargs={
                "model": "test-model",
                "model_base_url": "https://example.invalid/v1",
                "model_api_key": "key",
                "contest_host": "https://challenge.zc.tencent.com",
                "contest_token": "token",
                "runtime_dir": tmp_path / "runtime",
            },
            event_logger=logger,
            make_gateway=lambda settings: gateway,
            competition_runner=runner,
            sleep_fn=fake_sleep,
        )

    assert attempts == 2
    assert sleeps == [10, 20]
    assert any(event == "competition.supervisor_error" for event, _ in logger.events)
