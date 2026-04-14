from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.track3_stale_memory_cleanup import cleanup_track3_stale_memory


def test_cleanup_track3_stale_memory_deduplicates_colliding_sanitized_flag_records(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    code = "6RmRST2HkeTbwgbyMJaN"
    shared_prefix = "flag=flag{demo}\nprogress=1/4\n"
    store.add_challenge_memory(
        code,
        "persistent_flag_record",
        shared_prefix + "old foothold http://10.0.163.216/uploads/lv.php",
        source="submit_flag",
        persistent=True,
    )
    store.add_challenge_memory(
        code,
        "persistent_flag_record",
        shared_prefix + "old foothold http://10.0.163.217/uploads/lv.php",
        source="submit_flag",
        persistent=True,
    )

    summary = cleanup_track3_stale_memory(store)

    memories = [
        item for item in store.list_challenge_memories(code, limit=20)
        if item["memory_type"] == "persistent_flag_record"
    ]
    assert summary["sanitized_flag_records"] >= 1
    assert len(memories) == 1
    assert "flag=flag{demo}" in memories[0]["content"]
    assert "progress=1/4" in memories[0]["content"]
    assert "10.0.163." not in memories[0]["content"]
    assert "/uploads/lv.php" not in memories[0]["content"]
