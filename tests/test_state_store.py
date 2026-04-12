import sqlite3
from datetime import datetime, UTC

from niuniu_agent.state_store import StateStore


def test_state_store_records_submitted_flag(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.record_submitted_flag("challenge-1", "flag{demo}")

    assert store.has_submitted_flag("challenge-1", "flag{demo}") is True
    assert store.has_submitted_flag("challenge-1", "flag{other}") is False
    assert store.list_submitted_flags("challenge-1") == ["flag{demo}"]


def test_state_store_can_clear_submitted_flags_and_read_latest_timestamp(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.record_submitted_flag("challenge-1", "flag{demo}")

    latest = store.latest_submitted_flag_at("challenge-1")
    cleared = store.clear_submitted_flags("challenge-1")

    assert latest is not None
    assert cleared == 1
    assert store.list_submitted_flags("challenge-1") == []


def test_state_store_tracks_runtime_failure_state(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.mark_active_challenge("challenge-1")
    active_state = store.get_challenge_runtime_state("challenge-1")
    first_attempt_started_at = active_state["attempt_started_at"]
    first_failure = store.record_challenge_failure("challenge-1", "boom")
    second_failure = store.record_challenge_failure("challenge-1", "still boom")
    runtime_state = store.get_challenge_runtime_state("challenge-1")
    store.mark_active_challenge("challenge-1")
    retried_state = store.get_challenge_runtime_state("challenge-1")
    store.record_challenge_success("challenge-1")
    reset_state = store.get_challenge_runtime_state("challenge-1")

    assert first_failure == 1
    assert second_failure == 2
    assert active_state["active"] is True
    assert active_state["attempt_count"] == 1
    assert active_state["attempt_started_at"] is not None
    assert runtime_state["active"] is False
    assert runtime_state["failure_count"] == 2
    assert runtime_state["last_error"] == "still boom"
    assert runtime_state["attempt_started_at"] is None
    assert runtime_state["attempt_count"] == 1
    assert retried_state["active"] is True
    assert retried_state["attempt_count"] == 2
    assert retried_state["attempt_started_at"] != first_attempt_started_at
    assert reset_state["active"] is False
    assert reset_state["failure_count"] == 0
    assert reset_state["attempt_started_at"] is None
    assert reset_state["defer_until"] is None


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


def test_state_store_can_defer_one_challenge_attempt(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.mark_active_challenge("challenge-1")
    store.defer_challenge("challenge-1", defer_seconds=300, reason="long running", now=1000.0)
    state = store.get_challenge_runtime_state("challenge-1")

    assert state["active"] is False
    assert state["attempt_started_at"] is None
    assert state["defer_until"] == 1300.0
    assert state["last_error"] == "long running"
    assert store.is_challenge_deferred("challenge-1", now=1200.0) is True
    assert store.is_challenge_deferred("challenge-1", now=1301.0) is False
    assert store.seconds_until_dispatchable("challenge-1", now=1200.0) == 100.0


def test_state_store_persists_deduplicated_challenge_memories(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.add_challenge_memory("challenge-1", "turn_summary", "found admin path", source="worker")
    store.add_challenge_memory("challenge-1", "turn_summary", "found admin path", source="worker")
    store.add_challenge_memory("challenge-1", "credential_hint", "token=demo", source="worker")

    memories = store.list_challenge_memories("challenge-1", limit=10)

    assert len(memories) == 2
    assert memories[0]["memory_type"] == "credential_hint"
    assert memories[1]["memory_type"] == "turn_summary"


def test_state_store_can_clear_runtime_memory(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.record_submitted_flag("challenge-1", "flag{demo}")
    store.mark_active_challenge("challenge-1")
    store.mark_progress("challenge-1")
    store.add_history_event("challenge-1", "turn_completed", "summary")
    store.set_challenge_note("challenge-1", "foothold", "www-data shell")
    store.add_challenge_memory("challenge-1", "turn_summary", "summary", source="worker")
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

    cleared = store.clear_runtime_memory()

    assert cleared["submitted_flags"] == 1
    assert store.list_submitted_flags("challenge-1") == []
    assert store.list_history("challenge-1") == []
    assert store.get_challenge_notes("challenge-1") == {}
    assert store.list_challenge_memories("challenge-1") == []
    assert store.list_agent_statuses() == []
    assert store.list_agent_events() == []
    assert store.get_challenge_runtime_state("challenge-1")["attempt_count"] == 0


def test_state_store_persists_model_provider_selection_and_health(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.set_runtime_option("selected_model_provider_id", "rightcodes")
    store.set_runtime_option("selected_model_override", "gpt-5.4-xhigh")
    store.record_model_provider_failure("official", "timeout", now=1000.0)
    store.record_model_provider_success("rightcodes", now=1010.0)

    assert store.get_runtime_option("selected_model_provider_id") == "rightcodes"
    assert store.get_runtime_option("selected_model_override") == "gpt-5.4-xhigh"
    official_state = store.get_model_provider_state("official")
    rightcodes_state = store.get_model_provider_state("rightcodes")
    assert official_state["consecutive_failures"] == 1
    assert official_state["last_error"] == "timeout"
    assert rightcodes_state["total_successes"] == 1


def test_state_store_tracks_latest_agent_activity_timestamp(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.upsert_agent_status(
        agent_id="worker:c1:run1",
        role="challenge_worker",
        challenge_code="c1",
        status="running",
        summary="working",
        metadata={},
    )
    store.append_agent_event(
        agent_id="worker:c1:run1",
        challenge_code="c1",
        event_type="tool_start",
        payload="http_request",
    )

    activity = store.get_agent_last_activity("worker:c1:run1")

    assert activity is not None
    now = datetime.now(UTC).timestamp()
    assert abs(now - activity) < 10


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


def test_state_store_can_clear_agent_status_without_deleting_events(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.upsert_agent_status(
        agent_id="worker:challenge-1",
        role="challenge_worker",
        challenge_code="challenge-1",
        status="completed",
        summary="challenge completed",
        metadata={"challenge_code": "challenge-1"},
    )
    store.append_agent_event(
        agent_id="worker:challenge-1",
        challenge_code="challenge-1",
        event_type="worker_turn_completed",
        payload="done",
    )

    store.delete_agent_status("worker:challenge-1")

    assert store.get_agent_status("worker:challenge-1") is None
    assert store.list_agent_events(agent_id="worker:challenge-1")[0]["event_type"] == "worker_turn_completed"


def test_state_store_can_clear_worker_statuses_for_one_challenge(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.upsert_agent_status(
        agent_id="worker:c1:old",
        role="challenge_worker",
        challenge_code="c1",
        status="error",
        summary="old worker",
        metadata={},
    )
    store.upsert_agent_status(
        agent_id="worker:c2:keep",
        role="challenge_worker",
        challenge_code="c2",
        status="running",
        summary="other worker",
        metadata={},
    )

    store.delete_agent_statuses_for_challenge("c1", role="challenge_worker")

    assert store.get_agent_status("worker:c1:old") is None
    assert store.get_agent_status("worker:c2:keep") is not None


def test_state_store_can_clear_only_non_completed_worker_statuses(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    store.upsert_agent_status(
        agent_id="worker:c1:completed",
        role="challenge_worker",
        challenge_code="c1",
        status="completed",
        summary="done",
        metadata={},
    )
    store.upsert_agent_status(
        agent_id="worker:c1:error",
        role="challenge_worker",
        challenge_code="c1",
        status="error",
        summary="old error",
        metadata={},
    )

    store.delete_agent_statuses_for_challenge(
        "c1",
        role="challenge_worker",
        exclude_statuses={"completed"},
    )

    assert store.get_agent_status("worker:c1:completed") is not None
    assert store.get_agent_status("worker:c1:error") is None
