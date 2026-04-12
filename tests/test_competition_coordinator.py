import asyncio

import pytest

from niuniu_agent.runtime.coordinator import CompetitionCoordinator


@pytest.mark.anyio
async def test_competition_coordinator_respects_parallel_limit() -> None:
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)
    started = []
    blocker = asyncio.Event()

    async def worker(code: str) -> None:
        started.append(code)
        await blocker.wait()

    scheduled = await coordinator.schedule(["c1", "c2", "c3", "c4"], worker)

    assert scheduled == ["c1", "c2", "c3"]
    assert coordinator.active_count() == 3

    blocker.set()
    await coordinator.stop_all()


@pytest.mark.anyio
async def test_competition_coordinator_can_cancel_one_worker() -> None:
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)
    cancelled = []
    blocker = asyncio.Event()

    async def worker(code: str) -> None:
        try:
            await blocker.wait()
        except asyncio.CancelledError:
            cancelled.append(code)
            raise

    await coordinator.schedule(["c1"], worker)
    await asyncio.sleep(0)
    await coordinator.cancel_worker("c1")
    await asyncio.sleep(0)

    assert cancelled == ["c1"]
    assert coordinator.is_running("c1") is False
