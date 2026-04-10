from niuniu_agent.state_store import StateStore


def test_state_store_records_submitted_flag(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.record_submitted_flag("challenge-1", "flag{demo}")

    assert store.has_submitted_flag("challenge-1", "flag{demo}") is True
    assert store.has_submitted_flag("challenge-1", "flag{other}") is False
    assert store.list_submitted_flags("challenge-1") == ["flag{demo}"]


def test_state_store_tracks_runtime_failure_state(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.mark_active_challenge("challenge-1")
    first_failure = store.record_challenge_failure("challenge-1", "boom")
    second_failure = store.record_challenge_failure("challenge-1", "still boom")
    runtime_state = store.get_challenge_runtime_state("challenge-1")
    store.record_challenge_success("challenge-1")
    reset_state = store.get_challenge_runtime_state("challenge-1")

    assert first_failure == 1
    assert second_failure == 2
    assert runtime_state["active"] is True
    assert runtime_state["failure_count"] == 2
    assert runtime_state["last_error"] == "still boom"
    assert reset_state["active"] is False
    assert reset_state["failure_count"] == 0


def test_state_store_persists_history_and_notes(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.add_history_event("challenge-1", "turn_completed", "summary")
    store.set_challenge_note("challenge-1", "foothold", "www-data shell")

    history = store.list_history("challenge-1", limit=5)
    notes = store.get_challenge_notes("challenge-1")

    assert history[0]["event_type"] == "turn_completed"
    assert history[0]["payload"] == "summary"
    assert notes["foothold"] == "www-data shell"
