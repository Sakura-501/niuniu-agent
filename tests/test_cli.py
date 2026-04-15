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
    store.add_challenge_memory("c1", "persistent_flag_record", "keep me", source="seed", persistent=True)
    store.add_challenge_memory("c1", "persistent_hint", "old hint", source="worker:c1:old", persistent=True)
    store.add_challenge_memory("c1", "persistent_flag_record", "flag=flag{demo}\nprogress=1/4", source="submit_flag", persistent=True)
    store.add_challenge_memory("c1", "persistent_credential_hint", "password: 12345678", source="runtime", persistent=True)
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
    memories = store.list_challenge_memories("c1")
    assert len(memories) == 1
    assert memories[0]["persistent"] is True
    assert memories[0]["source"] == "seed"


def test_cli_can_clean_track3_stale_memory(tmp_path) -> None:
    runner = CliRunner()
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    store = StateStore(runtime_dir / "state.db")

    code = "6RmRST2HkeTbwgbyMJaN"
    store.set_challenge_note(code, "hint_content", "keep me")
    store.set_challenge_note(code, "provisional_findings", "old foothold 10.0.163.216 via /uploads/lv.php")
    store.add_challenge_memory(code, "persistent_hint", "keep hint", source="worker", persistent=True)
    store.add_challenge_memory(code, "persistent_provisional_findings", "old foothold 10.0.163.216 via /uploads/lv.php", source="worker", persistent=True)
    store.add_challenge_memory(
        code,
        "persistent_flag_record",
        "flag=flag{demo}\nprogress=1/4\nold foothold http://10.0.163.216/uploads/lv.php and 172.19.0.2:8080",
        source="worker",
        persistent=True,
    )

    result = runner.invoke(
        app,
        ["clean-track3-stale-memory", "--runtime-dir", str(runtime_dir), "--yes"],
    )

    assert result.exit_code == 0
    assert store.get_challenge_notes(code)["hint_content"] == "keep me"
    assert "provisional_findings" not in store.get_challenge_notes(code)
    memories = store.list_challenge_memories(code, limit=20)
    memory_types = {item["memory_type"] for item in memories}
    assert "persistent_hint" in memory_types
    assert "persistent_provisional_findings" not in memory_types
    sanitized_flag_record = next(item for item in memories if item["memory_type"] == "persistent_flag_record")
    assert "flag=flag{demo}" in sanitized_flag_record["content"]
    assert "10.0.163.216" not in sanitized_flag_record["content"]
    assert "/uploads/lv.php" not in sanitized_flag_record["content"]


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
        return None

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
async def test_competition_supervisor_uncancels_after_self_cancellation(tmp_path) -> None:
    gateway = DummyGateway()
    logger = DummyLogger()
    sleeps = []

    async def runner(context) -> None:
        task = asyncio.current_task()
        assert task is not None
        task.cancel("internal cancellation")
        await asyncio.sleep(0)

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
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

    assert sleeps == [10]
    assert any(event == "competition.supervisor_error" for event, _ in logger.events)
