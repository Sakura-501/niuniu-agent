from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace
import asyncio

from niuniu_agent.web.service import (
    AgentWebService,
    CompetitionProcessController,
    build_challenge_scheduler_view,
    build_agent_overview_rows,
    build_agent_tree,
)


def test_build_agent_overview_rows_keeps_only_real_agents() -> None:
    rows = build_agent_overview_rows(
        stored_agents=[
            {
                "agent_id": "manager:competition:run1",
                "role": "manager",
                "challenge_code": None,
                "status": "running",
                "summary": "ok",
                "metadata": {},
                "last_error": None,
                "updated_at": "now",
            },
            {
                "agent_id": "worker:done",
                "role": "challenge_worker",
                "challenge_code": "c1",
                "status": "completed",
                "summary": "done",
                "metadata": {},
                "last_error": None,
                "updated_at": "now",
            },
        ],
        process_status={"competition": {"running": True, "run_id": "run1"}},
        max_parallel_workers=3,
    )

    agent_ids = [row["agent_id"] for row in rows]

    assert "worker:done" in agent_ids
    assert all(not agent_id.startswith("worker-slot:") for agent_id in agent_ids)


def test_build_agent_tree_groups_workers_under_manager_run() -> None:
    tree = build_agent_tree(
        stored_agents=[
            {
                "agent_id": "manager:competition:run1",
                "role": "manager",
                "challenge_code": None,
                "status": "running",
                "summary": "manager",
                "metadata": {"run_id": "run1"},
                "last_error": None,
                "updated_at": "now",
            },
            {
                "agent_id": "worker:c1:abc",
                "role": "challenge_worker",
                "challenge_code": "c1",
                "status": "completed",
                "summary": "done",
                "metadata": {"competition_run_id": "run1", "manager_agent_id": "manager:competition:run1"},
                "last_error": None,
                "updated_at": "now",
            },
        ],
        process_status={"competition": {"running": True, "run_id": "run1"}},
        max_parallel_workers=3,
    )

    assert tree[0]["manager"]["agent_id"] == "manager:competition:run1"
    assert tree[0]["workers"][0]["agent_id"] == "worker:c1:abc"


def test_build_agent_tree_does_not_add_synthetic_manager_when_real_manager_exists_without_process_run_id() -> None:
    tree = build_agent_tree(
        stored_agents=[
            {
                "agent_id": "manager:competition:run1",
                "role": "manager",
                "challenge_code": None,
                "status": "running",
                "summary": "manager",
                "metadata": {"run_id": "run1"},
                "last_error": None,
                "updated_at": "now",
            },
        ],
        process_status={"competition": {"running": True, "run_id": None}},
        max_parallel_workers=3,
    )

    manager_ids = [group["manager"]["agent_id"] for group in tree]
    assert manager_ids == ["manager:competition:run1"]


def test_build_agent_tree_groups_orphan_workers_under_archived_manager() -> None:
    tree = build_agent_tree(
        stored_agents=[
            {
                "agent_id": "worker:c1:done",
                "role": "challenge_worker",
                "challenge_code": "c1",
                "status": "completed",
                "summary": "done",
                "metadata": {"competition_run_id": "run-old", "manager_agent_id": "manager:competition:run-old"},
                "last_error": None,
                "updated_at": "now",
            },
        ],
        process_status={"competition": {"running": False, "run_id": None}},
        max_parallel_workers=3,
    )

    manager_ids = [group["manager"]["agent_id"] for group in tree]
    assert "manager:competition:run-old" in manager_ids
    assert "manager:detached" not in manager_ids


def test_competition_process_controller_prefers_uv_launch_command() -> None:
    controller = CompetitionProcessController(
        repo_root=Path("/tmp/repo"),
        runtime_dir=Path("/tmp/repo/runtime"),
        web_port=8081,
    )

    command = controller._build_competition_command(prefer_uv=True)

    assert command == ["uv", "run", "niuniu-agent", "run", "--mode", "competition"]


def test_competition_process_controller_ignores_stale_pid_for_unrelated_process(tmp_path) -> None:
    controller = CompetitionProcessController(
        repo_root=Path("/tmp/repo"),
        runtime_dir=tmp_path / "runtime",
        web_port=8081,
    )
    sleeper = subprocess.Popen(["sleep", "30"])
    try:
        controller.competition_pid_file.write_text(str(sleeper.pid), encoding="utf-8")
        controller.competition_run_id_file.write_text("run-stale", encoding="utf-8")

        status = controller.status()

        assert status["competition"]["running"] is False
    finally:
        sleeper.terminate()
        sleeper.wait(timeout=5)


def test_build_challenge_scheduler_view_marks_dispatchable_and_paused_and_running() -> None:
    dispatchable = build_challenge_scheduler_view(
        {
            "code": "c1",
            "completed": False,
            "notes": {},
            "runtime_state": {},
        },
        [],
    )
    paused = build_challenge_scheduler_view(
        {
            "code": "c2",
            "completed": False,
            "notes": {"operator_pause": "true"},
            "runtime_state": {},
        },
        [],
    )
    running = build_challenge_scheduler_view(
        {
            "code": "c3",
            "completed": False,
            "notes": {},
            "runtime_state": {},
        },
        [{"agent_id": "worker:c3:run1", "status": "running"}],
    )

    assert dispatchable["scheduler_status"] == "dispatchable"
    assert paused["scheduler_status"] == "paused"
    assert running["scheduler_status"] == "running"


def test_build_challenge_scheduler_view_marks_deferred() -> None:
    deferred = build_challenge_scheduler_view(
        {
            "code": "c9",
            "completed": False,
            "notes": {},
            "runtime_state": {"defer_until": 4102444800.0},
        },
        [],
    )

    assert deferred["scheduler_status"] == "deferred"


def test_agent_web_service_overview_reconnects_gateway_after_session_reset() -> None:
    class FlakyStore:
        def __init__(self) -> None:
            self.calls = 0

        async def refresh(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Server not initialized. Make sure you call `connect()` first.")
            return SimpleNamespace(current_level=1, total_challenges=0, solved_challenges=0, challenges=[])

        def export_json(self, snapshot):
            return {"challenges": []}

    class DummyGateway:
        def __init__(self) -> None:
            self.reconnect_calls = 0

        async def reconnect(self) -> None:
            self.reconnect_calls += 1

    class DummyState:
        def list_agent_statuses(self, **kwargs):
            return []

        def list_agent_events(self, **kwargs):
            return []

    service = AgentWebService()
    service.settings = SimpleNamespace(web_port=8081, callback_resource=None)
    service.contest_gateway = DummyGateway()
    service.context = SimpleNamespace(
        settings=service.settings,
        challenge_store=FlakyStore(),
        state_store=DummyState(),
        provider_router=None,
    )
    service.controller = SimpleNamespace(status=lambda: {"competition": {"running": False}, "ui": {"running": True}})

    result = asyncio.run(service.overview())

    assert result["contest"]["challenges"] == []
    assert service.contest_gateway.reconnect_calls == 1
