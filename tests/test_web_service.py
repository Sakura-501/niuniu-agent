from __future__ import annotations

from niuniu_agent.web.service import build_agent_overview_rows


def test_build_agent_overview_rows_keeps_completed_workers_but_preserves_free_slots() -> None:
    rows = build_agent_overview_rows(
        stored_agents=[
            {
                "agent_id": "manager:competition",
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
        process_status={"competition": {"running": True}},
        max_parallel_workers=3,
    )

    agent_ids = [row["agent_id"] for row in rows]

    assert "worker:done" in agent_ids
    assert "worker-slot:1" in agent_ids
