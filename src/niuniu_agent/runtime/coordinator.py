from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class CompetitionCoordinator:
    def __init__(self, max_parallel_challenges: int = 3) -> None:
        self.max_parallel_challenges = max_parallel_challenges
        self.worker_tasks: dict[str, asyncio.Task] = {}

    def active_count(self) -> int:
        return sum(1 for task in self.worker_tasks.values() if not task.done())

    def prune_finished(self) -> None:
        for code, task in list(self.worker_tasks.items()):
            if task.done():
                self.worker_tasks.pop(code, None)

    def is_running(self, challenge_code: str) -> bool:
        task = self.worker_tasks.get(challenge_code)
        return task is not None and not task.done()

    async def schedule(
        self,
        challenge_codes: list[str],
        worker_factory: Callable[[str], Awaitable[None]],
    ) -> list[str]:
        self.prune_finished()
        started: list[str] = []
        for code in challenge_codes:
            if self.active_count() >= self.max_parallel_challenges:
                break
            if self.is_running(code):
                continue
            self.worker_tasks[code] = asyncio.create_task(worker_factory(code), name=f"challenge-worker-{code}")
            started.append(code)
        return started

    async def stop_all(self) -> None:
        tasks = [task for task in self.worker_tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
