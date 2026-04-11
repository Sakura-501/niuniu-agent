from __future__ import annotations

from niuniu_agent.web.service import build_agent_overview_rows, build_agent_tree


def test_build_agent_overview_rows_keeps_completed_workers_but_preserves_free_slots() -> None:
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
    assert "worker-slot:1" in agent_ids


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
