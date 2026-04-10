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
