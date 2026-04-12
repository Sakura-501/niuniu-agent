from __future__ import annotations

from pathlib import Path

from niuniu_agent.web.service import (
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


def test_competition_process_controller_prefers_uv_launch_command() -> None:
    controller = CompetitionProcessController(
        repo_root=Path("/tmp/repo"),
        runtime_dir=Path("/tmp/repo/runtime"),
        web_port=8081,
    )

    command = controller._build_competition_command(prefer_uv=True)

    assert command == ["uv", "run", "niuniu-agent", "run", "--mode", "competition"]


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
