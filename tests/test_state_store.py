from niuniu_agent.state_store import StateStore


def test_state_store_records_submitted_flag(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.record_submitted_flag("challenge-1", "flag{demo}")

    assert store.has_submitted_flag("challenge-1", "flag{demo}") is True
    assert store.has_submitted_flag("challenge-1", "flag{other}") is False
    assert store.list_submitted_flags("challenge-1") == ["flag{demo}"]
