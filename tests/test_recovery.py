from types import SimpleNamespace

from niuniu_agent.runtime.recovery import recover_competition_state
from niuniu_agent.state_store import StateStore


def _snapshot(*challenges):
    return SimpleNamespace(challenges=list(challenges))


def _challenge(code: str, *, completed: bool = False, flag_count: int = 1, flag_got_count: int = 0):
    return SimpleNamespace(
        code=code,
        completed=completed,
        flag_count=flag_count,
        flag_got_count=flag_got_count,
    )


def test_recover_competition_state_clears_stale_agents_and_completed_runtime(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.record_submitted_flag("c1", "flag{done}")
    store.mark_active_challenge("c1")
    store.record_challenge_failure("c1", "boom")
    store.upsert_agent_status(
        agent_id="manager:competition:oldrun",
        role="manager",
        challenge_code=None,
        status="running",
        summary="old manager",
        metadata={"run_id": "oldrun"},
    )
    store.upsert_agent_status(
        agent_id="worker:c2:oldrun",
        role="challenge_worker",
        challenge_code="c2",
        status="error",
        summary="old worker",
        metadata={"competition_run_id": "oldrun"},
    )

    summary = recover_competition_state(
        snapshot=_snapshot(_challenge("c1", completed=False, flag_count=1, flag_got_count=0), _challenge("c2")),
        state_store=store,
        competition_run_id="newrun",
    )

    assert summary["normalized_completed_challenges"] == ["c1"]
    assert "worker:c2:oldrun" in summary["removed_stale_agents"]
    assert store.get_challenge_runtime_state("c1")["active"] is False
    assert store.get_agent_status("worker:c2:oldrun") is None
