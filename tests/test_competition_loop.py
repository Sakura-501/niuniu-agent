from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from niuniu_agent.config import AgentSettings
from niuniu_agent.runtime.competition_loop import (
    recover_stalled_workers,
    retire_completed_workers,
    run_competition_loop,
)
from niuniu_agent.runtime.coordinator import CompetitionCoordinator
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.state_store import StateStore
from niuniu_agent.control_plane.models import ChallengeSnapshot


class RefreshFlakyStore:
    def __init__(self) -> None:
        self.calls = 0

    async def refresh(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("Error calling tool 'list_challenges': 请求频率超出限制，每秒最多调用3次")
        return SimpleNamespace(current_level=1, total_challenges=0, solved_challenges=0, challenges=[])


class DummyStateStore:
    def list_agent_statuses(self, **kwargs):
        return []

    def upsert_agent_status(self, *args, **kwargs):
        return None

    def append_agent_event(self, *args, **kwargs):
        return None


class DummyEventLogger:
    def __init__(self) -> None:
        self.events = []

    def log(self, event, payload=None):
        self.events.append((event, payload or {}))


@pytest.mark.anyio
async def test_competition_loop_survives_refresh_rate_limit() -> None:
    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
            competition_idle_sleep_seconds=1,
        ),
        contest_gateway=object(),
        challenge_store=RefreshFlakyStore(),
        state_store=DummyStateStore(),
        event_logger=DummyEventLogger(),
        local_toolbox=object(),
        skill_registry=None,
    )

    task = asyncio.create_task(run_competition_loop(context))
    await asyncio.sleep(1.2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert context.challenge_store.calls >= 2
    assert any(event == "competition.refresh_error" for event, _ in context.event_logger.events)


@pytest.mark.anyio
async def test_recover_stalled_workers_cancels_stale_running_worker(tmp_path) -> None:
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)
    blocker = asyncio.Event()
    cancelled = []

    async def worker(code: str) -> None:
        try:
            await blocker.wait()
        except asyncio.CancelledError:
            cancelled.append(code)
            raise

    await coordinator.schedule(["c1"], worker)
    await asyncio.sleep(0)

    state_store = StateStore(tmp_path / "state.db")
    state_store.upsert_agent_status(
        agent_id="worker:c1:run1",
        role="challenge_worker",
        challenge_code="c1",
        status="running",
        summary="recon",
        metadata={},
    )
    state_store.append_agent_event(
        agent_id="worker:c1:run1",
        challenge_code="c1",
        event_type="tool_start",
        payload="http_request",
    )
    old = "2026-01-01 00:00:00"
    with state_store._connect() as connection:
        connection.execute("UPDATE agent_status SET updated_at = ? WHERE agent_id = ?", (old, "worker:c1:run1"))
        connection.execute("UPDATE agent_events SET created_at = ? WHERE agent_id = ?", (old, "worker:c1:run1"))

    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
            competition_worker_stall_seconds=60,
        ),
        contest_gateway=object(),
        challenge_store=object(),
        state_store=state_store,
        event_logger=DummyEventLogger(),
        local_toolbox=object(),
        skill_registry=None,
        agent_id="manager:competition:run1",
        agent_role="manager",
    )

    recovered = await recover_stalled_workers(
        snapshot=SimpleNamespace(challenges=[]),
        context=context,
        coordinator=coordinator,
        stall_seconds=60,
        now=9999999999.0,
    )

    assert recovered[0]["challenge_code"] == "c1"
    assert cancelled == ["c1"]
    assert state_store.get_agent_status("worker:c1:run1")["status"] == "waiting_recovery"


@pytest.mark.anyio
async def test_retire_completed_workers_cancels_running_worker_on_completed_challenge(tmp_path) -> None:
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)
    blocker = asyncio.Event()
    cancelled = []

    async def worker(code: str) -> None:
        try:
            await blocker.wait()
        except asyncio.CancelledError:
            cancelled.append(code)
            raise

    await coordinator.schedule(["c1"], worker)
    await asyncio.sleep(0)

    state_store = StateStore(tmp_path / "state.db")
    state_store.upsert_agent_status(
        agent_id="worker:c1:run1",
        role="challenge_worker",
        challenge_code="c1",
        status="running",
        summary="recon",
        metadata={"competition_run_id": "run1"},
    )

    class ChallengeStoreStub:
        @staticmethod
        def is_effectively_completed(challenge):
            return True

    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
        ),
        contest_gateway=object(),
        challenge_store=ChallengeStoreStub(),
        state_store=state_store,
        event_logger=DummyEventLogger(),
        local_toolbox=object(),
        skill_registry=None,
    )

    retired = await retire_completed_workers(
        snapshot=SimpleNamespace(
            challenges=[
                ChallengeSnapshot(
                    code="c1",
                    title="done",
                    description="demo",
                    difficulty="easy",
                    level=0,
                    flag_count=1,
                    flag_got_count=1,
                    instance_status="stopped",
                )
            ]
        ),
        context=context,
        coordinator=coordinator,
    )

    assert retired == [{"agent_id": "worker:c1:run1", "challenge_code": "c1"}]
    assert cancelled == ["c1"]
    assert state_store.get_agent_status("worker:c1:run1")["status"] == "completed"
