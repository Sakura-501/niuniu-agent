from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.challenge_memory_seeds import apply_seed_memories


def test_apply_seed_memories_persists_key_challenge_strategies(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    apply_seed_memories(store)

    bpoxy = store.list_challenge_memories("BpOxyTLXpdveWilhjRCFjZtMGjgr", limit=10)
    gradio = store.list_challenge_memories("3ZdueytTkJeRy2wiYmJiqwrzP2XiNqs", limit=10)

    assert bpoxy
    assert gradio
    assert bpoxy[0]["persistent"] is True
    assert gradio[0]["persistent"] is True
