from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.challenge_memory_seeds import apply_seed_memories


def test_apply_seed_memories_persists_key_challenge_strategies(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    apply_seed_memories(store)

    bpoxy = store.list_challenge_memories("BpOxyTLXpdveWilhjRCFjZtMGjgr", limit=10)
    gradio = store.list_challenge_memories("3ZdueytTkJeRy2wiYmJiqwrzP2XiNqs", limit=10)
    track3_link = store.list_challenge_memories("6RmRST2HkeTbwgbyMJaN", limit=10)
    track3_layer = store.list_challenge_memories("K7kbx40FbhQNODZkS", limit=10)
    track3_firewall = store.list_challenge_memories("2ihdUTWqg7iVcvvD7GAZzOadCxS", limit=10)

    assert bpoxy
    assert gradio
    assert track3_link
    assert track3_layer
    assert track3_firewall
    assert bpoxy[0]["persistent"] is True
    assert gradio[0]["persistent"] is True
    assert any(item["memory_type"] == "operator_strategy" and item["persistent"] is True for item in track3_link)
    assert any(item["memory_type"] == "operator_strategy" and item["persistent"] is True for item in track3_layer)
    assert any(item["memory_type"] == "operator_strategy" and item["persistent"] is True for item in track3_firewall)
