from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from niuniu_agent.config import AgentSettings
from niuniu_agent.runtime.competition_loop import (
    close_orphaned_challenge_instances,
    close_completed_challenge_instances,
    ensure_challenge_instance_running,
    ensure_worker_target_instance_ready,
    recover_stalled_workers,
    stop_challenge_instance_before_worker_exit,
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


class RefreshCancelledStore:
    def __init__(self) -> None:
        self.calls = 0

    async def refresh(self):
        self.calls += 1
        if self.calls == 1:
            raise asyncio.CancelledError()
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


class DummyContestGateway:
    def __init__(self) -> None:
        self.stopped: list[str] = []
        self.started: list[str] = []

    async def stop_challenge(self, code: str):
        self.stopped.append(code)
        return {"ok": True}

    async def start_challenge(self, code: str):
        self.started.append(code)
        return {"ok": True, "entrypoint": ["127.0.0.1:8080"]}


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
async def test_competition_loop_survives_internal_refresh_cancelled_error() -> None:
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
        challenge_store=RefreshCancelledStore(),
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

    gateway = DummyContestGateway()
    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
        ),
        contest_gateway=gateway,
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
                    instance_status="running",
                )
            ]
        ),
        context=context,
        coordinator=coordinator,
    )

    assert retired == [{"agent_id": "worker:c1:run1", "challenge_code": "c1"}]
    assert cancelled == ["c1"]
    assert gateway.stopped == ["c1"]
    assert state_store.get_agent_status("worker:c1:run1")["status"] == "completed"


@pytest.mark.anyio
async def test_close_completed_challenge_instances_closes_running_instance_even_without_worker(tmp_path) -> None:
    state_store = StateStore(tmp_path / "state.db")
    state_store.record_submitted_flag("c1", "flag{demo}")
    gateway = DummyContestGateway()
    logger = DummyEventLogger()

    class ChallengeStoreStub:
        def __init__(self, store):
            self.store = store

        def is_effectively_completed(self, challenge):
            return True

    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=ChallengeStoreStub(state_store),
        state_store=state_store,
        event_logger=logger,
        local_toolbox=object(),
        skill_registry=None,
    )

    closed = await close_completed_challenge_instances(
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
                    instance_status="running",
                )
            ]
        ),
        context=context,
    )

    assert closed == ["c1"]
    assert gateway.stopped == ["c1"]


@pytest.mark.anyio
async def test_close_orphaned_challenge_instances_stops_running_instance_without_worker(tmp_path) -> None:
    state_store = StateStore(tmp_path / "state.db")
    gateway = DummyContestGateway()
    logger = DummyEventLogger()
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)

    class ChallengeStoreStub:
        @staticmethod
        def is_effectively_completed(challenge):
            return False

    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=ChallengeStoreStub(),
        state_store=state_store,
        event_logger=logger,
        local_toolbox=object(),
        skill_registry=None,
    )

    closed = await close_orphaned_challenge_instances(
        snapshot=SimpleNamespace(
            challenges=[
                ChallengeSnapshot(
                    code="c1",
                    title="demo",
                    description="demo",
                    difficulty="easy",
                    level=0,
                    flag_count=1,
                    flag_got_count=0,
                    instance_status="running",
                )
            ]
        ),
        context=context,
        coordinator=coordinator,
    )

    assert closed == ["c1"]
    assert gateway.stopped == ["c1"]


@pytest.mark.anyio
async def test_close_orphaned_challenge_instances_keeps_running_instance_with_live_worker(tmp_path) -> None:
    state_store = StateStore(tmp_path / "state.db")
    gateway = DummyContestGateway()
    logger = DummyEventLogger()
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)
    blocker = asyncio.Event()

    async def worker(code: str) -> None:
        await blocker.wait()

    await coordinator.schedule(["c1"], worker)
    await asyncio.sleep(0)

    class ChallengeStoreStub:
        @staticmethod
        def is_effectively_completed(challenge):
            return False

    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=ChallengeStoreStub(),
        state_store=state_store,
        event_logger=logger,
        local_toolbox=object(),
        skill_registry=None,
    )

    closed = await close_orphaned_challenge_instances(
        snapshot=SimpleNamespace(
            challenges=[
                ChallengeSnapshot(
                    code="c1",
                    title="demo",
                    description="demo",
                    difficulty="easy",
                    level=0,
                    flag_count=1,
                    flag_got_count=0,
                    instance_status="running",
                )
            ]
        ),
        context=context,
        coordinator=coordinator,
    )

    assert closed == []
    assert gateway.stopped == []
    blocker.set()
    await coordinator.stop_all()


@pytest.mark.anyio
async def test_stop_challenge_instance_before_worker_exit_attempts_stop_when_state_unknown() -> None:
    gateway = DummyContestGateway()
    logger = DummyEventLogger()

    stopped = await stop_challenge_instance_before_worker_exit(
        contest_gateway=gateway,
        challenge_code="c1",
        instance_status=None,
        event_logger=logger,
        reason="worker exiting",
    )

    assert stopped is True
    assert gateway.stopped == ["c1"]


@pytest.mark.anyio
async def test_stop_challenge_instance_before_worker_exit_skips_known_stopped_instance() -> None:
    gateway = DummyContestGateway()
    logger = DummyEventLogger()

    stopped = await stop_challenge_instance_before_worker_exit(
        contest_gateway=gateway,
        challenge_code="c1",
        instance_status="stopped",
        event_logger=logger,
        reason="worker exiting",
    )

    assert stopped is False
    assert gateway.stopped == []


@pytest.mark.anyio
async def test_ensure_challenge_instance_running_starts_stopped_unsolved_challenge() -> None:
    gateway = DummyContestGateway()
    logger = DummyEventLogger()

    started = await ensure_challenge_instance_running(
        contest_gateway=gateway,
        challenge=ChallengeSnapshot(
            code="c1",
            title="demo",
            description="demo",
            difficulty="easy",
            level=0,
            flag_count=1,
            flag_got_count=0,
            instance_status="stopped",
            entrypoints=[],
        ),
        event_logger=logger,
    )

    assert started is True
    assert gateway.started == ["c1"]


@pytest.mark.anyio
async def test_ensure_challenge_instance_running_skips_running_or_completed_challenge() -> None:
    gateway = DummyContestGateway()
    logger = DummyEventLogger()

    started_running = await ensure_challenge_instance_running(
        contest_gateway=gateway,
        challenge=ChallengeSnapshot(
            code="c1",
            title="demo",
            description="demo",
            difficulty="easy",
            level=0,
            flag_count=1,
            flag_got_count=0,
            instance_status="running",
            entrypoints=["127.0.0.1:8080"],
        ),
        event_logger=logger,
    )
    started_completed = await ensure_challenge_instance_running(
        contest_gateway=gateway,
        challenge=ChallengeSnapshot(
            code="c2",
            title="done",
            description="demo",
            difficulty="easy",
            level=0,
            flag_count=1,
            flag_got_count=1,
            instance_status="stopped",
            entrypoints=[],
        ),
        event_logger=logger,
    )

    assert started_running is False
    assert started_completed is False
    assert gateway.started == []


@pytest.mark.anyio
async def test_ensure_worker_target_instance_ready_marks_waiting_when_instance_stays_stopped(tmp_path) -> None:
    state_store = StateStore(tmp_path / "state.db")
    gateway = DummyContestGateway()
    logger = DummyEventLogger()

    class ChallengeStoreStub:
        async def refresh(self):
            return SimpleNamespace(
                current_level=0,
                total_challenges=1,
                solved_challenges=0,
                challenges=[
                    ChallengeSnapshot(
                        code="c1",
                        title="demo",
                        description="demo",
                        difficulty="easy",
                        level=0,
                        flag_count=1,
                        flag_got_count=0,
                        instance_status="stopped",
                    )
                ],
            )

    context = RuntimeContext(
        settings=AgentSettings(
            model="test-model",
            model_base_url="https://example.invalid/v1",
            model_api_key="key",
            contest_host="https://challenge.zc.tencent.com",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=ChallengeStoreStub(),
        state_store=state_store,
        event_logger=logger,
        local_toolbox=object(),
        skill_registry=None,
        agent_id="worker:c1:test",
        agent_role="challenge_worker",
        challenge_code="c1",
    )

    target = ChallengeSnapshot(
        code="c1",
        title="demo",
        description="demo",
        difficulty="easy",
        level=0,
        flag_count=1,
        flag_got_count=0,
        instance_status="stopped",
    )

    refreshed, ready = await ensure_worker_target_instance_ready(
        worker_context=context,
        target=target,
        worker_agent_id="worker:c1:test",
        competition_run_id="run1",
        manager_agent_id="manager:competition:run1",
    )

    status = state_store.get_agent_status("worker:c1:test")

    assert ready is False
    assert refreshed.instance_status == "stopped"
    assert gateway.started == ["c1"]
    assert status is not None
    assert status["status"] == "waiting_instance"
