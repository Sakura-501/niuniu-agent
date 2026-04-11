from niuniu_agent.runtime.competition_loop import build_manager_agent_id, build_worker_agent_id


def test_build_worker_agent_id_is_unique_per_run() -> None:
    first = build_worker_agent_id("c1")
    second = build_worker_agent_id("c1")

    assert first.startswith("worker:c1:")
    assert second.startswith("worker:c1:")
    assert first != second


def test_build_manager_agent_id_uses_competition_run_id() -> None:
    assert build_manager_agent_id("run123") == "manager:competition:run123"
