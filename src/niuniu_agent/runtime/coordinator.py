from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable


class CompetitionCoordinator:
    def __init__(self, max_parallel_challenges: int = 3) -> None:
        self.max_parallel_challenges = max_parallel_challenges
        self.worker_tasks: dict[str, asyncio.Task] = {}
        self.worker_failures: dict[str, str] = {}

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
            task = asyncio.create_task(worker_factory(code), name=f"challenge-worker-{code}")
            task.add_done_callback(lambda done, challenge_code=code: self._consume_task_result(challenge_code, done))
            self.worker_tasks[code] = task
            started.append(code)
        return started

    async def stop_all(self) -> None:
        tasks = [task for task in self.worker_tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(*tasks, return_exceptions=True)

    def _consume_task_result(self, challenge_code: str, task: asyncio.Task) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            exc = task.exception()
            if exc is not None:
                self.worker_failures[challenge_code] = str(exc)
