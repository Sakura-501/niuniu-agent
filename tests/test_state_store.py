import sqlite3

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


def test_state_store_tracks_progress_timestamp(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.mark_progress("challenge-1")
    state = store.get_challenge_runtime_state("challenge-1")
    last_progress_at = state["last_progress_at"]
    elapsed = store.seconds_since_progress("challenge-1", now=float(last_progress_at) + 120)

    assert elapsed == 120


def test_state_store_migrates_old_runtime_schema(tmp_path) -> None:
    db_path = tmp_path / "state.db"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE challenge_runtime_state (
                challenge_code TEXT PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    store = StateStore(db_path)
    state = store.get_challenge_runtime_state("challenge-1")

    assert "last_progress_at" in state
    assert state["last_progress_at"] is None


def test_state_store_tracks_agent_runtime_status_and_events(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.upsert_agent_status(
        agent_id="worker:challenge-1",
        role="challenge_worker",
        challenge_code="challenge-1",
        status="running",
        summary="recon in progress",
        metadata={"stage": "recon"},
    )
    store.append_agent_event(
        agent_id="worker:challenge-1",
        challenge_code="challenge-1",
        event_type="tool_start",
        payload='{"tool":"http_request"}',
    )

    statuses = store.list_agent_statuses()
    events = store.list_agent_events(challenge_code="challenge-1")

    assert statuses[0]["agent_id"] == "worker:challenge-1"
    assert statuses[0]["role"] == "challenge_worker"
    assert statuses[0]["status"] == "running"
    assert statuses[0]["metadata"]["stage"] == "recon"
    assert events[0]["agent_id"] == "worker:challenge-1"
    assert events[0]["event_type"] == "tool_start"


def test_state_store_can_list_agent_events_in_ascending_order_and_delete_agent(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.upsert_agent_status(
        agent_id="debug:session-1",
        role="debug",
        challenge_code=None,
        status="idle",
        summary="session created",
        metadata={"session_id": "session-1"},
    )
    store.append_agent_event(
        agent_id="debug:session-1",
        challenge_code=None,
        event_type="debug_user_message",
        payload="hello",
    )
    store.append_agent_event(
        agent_id="debug:session-1",
        challenge_code=None,
        event_type="debug_assistant_message",
        payload="world",
    )

    ascending = store.list_agent_events(agent_id="debug:session-1", ascending=True)

    assert [item["event_type"] for item in ascending] == [
        "debug_user_message",
        "debug_assistant_message",
    ]

    store.delete_agent("debug:session-1")

    assert store.get_agent_status("debug:session-1") is None
    assert store.list_agent_events(agent_id="debug:session-1") == []
