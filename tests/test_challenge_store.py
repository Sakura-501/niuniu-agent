import pytest

from niuniu_agent.control_plane.challenge_store import ChallengeStore


class DummyContestClient:
    async def list_challenges(self):
        return {
            "current_level": 2,
            "total_challenges": 2,
            "solved_challenges": 1,
            "challenges": [
                {
                    "title": "done",
                    "code": "c1",
                    "difficulty": "easy",
                    "description": "finished one",
                    "level": 1,
                    "flag_count": 1,
                    "flag_got_count": 1,
                    "instance_status": "stopped",
                    "entrypoint": None,
                },
                {
                    "title": "todo",
                    "code": "c2",
                    "difficulty": "medium",
                    "description": "open target",
                    "level": 2,
                    "flag_count": 2,
                    "flag_got_count": 0,
                    "instance_status": "running",
                    "entrypoint": ["127.0.0.1:8080"],
                },
            ],
        }


class DummyStateStore:
    def __init__(self) -> None:
        self.history = []
        self.notes = {}
        self.memories = []

    def list_submitted_flags(self, challenge_code: str) -> list[str]:
        return ["flag{local}"] if challenge_code == "c2" else []

    def get_challenge_runtime_state(self, challenge_code: str) -> dict[str, object]:
        return {
            "active": False,
            "failure_count": 0,
            "last_error": None,
            "attempt_count": 0,
            "attempt_started_at": None,
            "defer_until": None,
        }

    def get_challenge_notes(self, challenge_code: str) -> dict[str, str]:
        return self.notes

    def list_history(self, challenge_code: str, limit: int = 10):
        return self.history[:limit]

    def list_challenge_memories(self, challenge_code: str, limit: int = 10):
        return self.memories[:limit]

    def delete_agent_statuses_for_challenge(self, challenge_code: str, *, role: str | None = None, exclude_statuses: set[str] | None = None):
        return None


@pytest.mark.anyio
async def test_challenge_store_refresh_and_next_candidate() -> None:
    store = ChallengeStore(DummyContestClient(), DummyStateStore())

    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    assert snapshot.current_level == 2
    assert challenge is not None
    assert challenge.code == "c2"
    assert "local_flags=1" in store.render_summary(snapshot)


@pytest.mark.anyio
async def test_challenge_store_next_candidate_prioritizes_current_level() -> None:
    class MultiLevelContestClient(DummyContestClient):
        async def list_challenges(self):
            return {
                "current_level": 1,
                "total_challenges": 2,
                "solved_challenges": 0,
                "challenges": [
                    {
                        "title": "old",
                        "code": "c-old",
                        "difficulty": "easy",
                        "description": "older zone",
                        "level": 0,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    },
                    {
                        "title": "new",
                        "code": "c-new",
                        "difficulty": "hard",
                        "description": "new zone",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    },
                ],
            }

    class EmptyFlagsState(DummyStateStore):
        def list_submitted_flags(self, challenge_code: str) -> list[str]:
            return []

    store = ChallengeStore(MultiLevelContestClient(), EmptyFlagsState())

    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    assert challenge is not None
    assert challenge.code == "c-new"


@pytest.mark.anyio
async def test_challenge_store_next_candidate_skips_locked_future_levels() -> None:
    class LockedContestClient(DummyContestClient):
        async def list_challenges(self):
            return {
                "current_level": 0,
                "total_challenges": 2,
                "solved_challenges": 0,
                "challenges": [
                    {
                        "title": "open",
                        "code": "c-open",
                        "difficulty": "easy",
                        "description": "open zone",
                        "level": 0,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    },
                    {
                        "title": "locked",
                        "code": "c-locked",
                        "difficulty": "easy",
                        "description": "locked zone",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    },
                ],
            }

    class EmptyFlagsState(DummyStateStore):
        def list_submitted_flags(self, challenge_code: str) -> list[str]:
            return []

    store = ChallengeStore(LockedContestClient(), EmptyFlagsState())

    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    assert challenge is not None
    assert challenge.code == "c-open"


@pytest.mark.anyio
async def test_challenge_store_autonomous_prompt_includes_history_and_notes() -> None:
    state = DummyStateStore()
    state.history = [{"event_type": "turn_completed", "payload": "summary", "created_at": "now"}]
    state.notes = {"foothold": "user shell"}
    state.memories = [{"memory_type": "turn_summary", "content": "summary", "source": "worker", "created_at": "now"}]
    store = ChallengeStore(DummyContestClient(), state)
    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    prompt = store.build_autonomous_prompt(snapshot, challenge)

    assert "turn_completed" in prompt
    assert "foothold" in prompt
    assert "turn_summary" in prompt


@pytest.mark.anyio
async def test_challenge_store_autonomous_prompt_omits_recursive_shared_findings_note() -> None:
    state = DummyStateStore()
    state.notes = {
        "foothold": "user shell",
        "shared_findings": "Shared findings: [manager] Recovered notes: {\"shared_findings\": \"nested\"}",
    }
    store = ChallengeStore(DummyContestClient(), state)
    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    prompt = store.build_autonomous_prompt(snapshot, challenge)

    assert "foothold" in prompt
    assert "shared_findings" not in prompt


@pytest.mark.anyio
async def test_challenge_store_autonomous_prompt_always_includes_persisted_hint_context() -> None:
    state = DummyStateStore()
    state.notes = {
        "hint_viewed": "true",
        "hint_content": "look at the JWT kid parser first",
    }
    state.history = [{"event_type": "hint_viewed", "payload": "look at the JWT kid parser first", "created_at": "now"}]
    store = ChallengeStore(DummyContestClient(), state)
    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    prompt = store.build_autonomous_prompt(snapshot, challenge)

    assert "hint_context" in prompt
    assert "JWT kid parser" in prompt


@pytest.mark.anyio
async def test_challenge_store_autonomous_prompt_recovers_hint_context_from_persistent_memory() -> None:
    state = DummyStateStore()
    state.memories = [
        {
            "memory_type": "persistent_hint",
            "content": "后台上传功能的后缀名检测不够全面。",
            "source": "worker:c2",
            "persistent": True,
            "created_at": "now",
        }
    ]
    store = ChallengeStore(DummyContestClient(), state)
    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    prompt = store.build_autonomous_prompt(snapshot, challenge)

    assert "hint_context" in prompt
    assert "后台上传功能的后缀名检测不够全面" in prompt


@pytest.mark.anyio
async def test_challenge_store_autonomous_prompt_for_worker_omits_global_contest_summary() -> None:
    state = DummyStateStore()
    state.notes = {"hint_viewed": "true", "hint_content": "check admin workflow"}
    store = ChallengeStore(DummyContestClient(), state)
    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    prompt = store.build_autonomous_prompt(snapshot, challenge)

    assert '"active_challenge"' in prompt
    assert '"hint_context"' in prompt
    assert '"total_challenges"' not in prompt
    assert '"solved_challenges"' not in prompt
    assert '"available_skills_catalog"' not in prompt


@pytest.mark.anyio
async def test_challenge_store_export_json_includes_official_fields_even_without_local_state() -> None:
    store = ChallengeStore(DummyContestClient(), DummyStateStore())

    snapshot = await store.refresh()
    exported = store.export_json(snapshot)
    challenge = next(item for item in exported["challenges"] if item["code"] == "c2")

    assert challenge["instance_status"] == "running"
    assert challenge["entrypoints"] == ["127.0.0.1:8080"]
    assert challenge["hint_viewed"] is False
    assert challenge["notes"] == {}
    assert challenge["recent_history"] == []
    assert challenge["recent_memories"] == []


@pytest.mark.anyio
async def test_challenge_store_treats_local_successful_flags_as_effective_completion() -> None:
    class LocalSolvedStateStore(DummyStateStore):
        def list_submitted_flags(self, challenge_code: str) -> list[str]:
            if challenge_code == "c2":
                return ["flag{one}", "flag{two}"]
            return []

    store = ChallengeStore(DummyContestClient(), LocalSolvedStateStore())

    snapshot = await store.refresh()
    challenge = next(item for item in snapshot.challenges if item.code == "c2")
    exported = store.export_json(snapshot)
    exported_challenge = next(item for item in exported["challenges"] if item["code"] == "c2")

    assert store.is_effectively_completed(challenge) is True
    assert store.next_candidate(snapshot) is None
    assert exported_challenge["completed"] is True
    assert exported["solved_challenges"] == 2


@pytest.mark.anyio
async def test_challenge_store_does_not_mark_high_track_unknown_flag_count_complete_from_single_local_flag() -> None:
    class HighTrackStateStore(DummyStateStore):
        def list_submitted_flags(self, challenge_code: str) -> list[str]:
            return ["flag{one}"] if challenge_code == "c2" else []

    class HighTrackContestClient(DummyContestClient):
        async def list_challenges(self):
            return {
                "current_level": 3,
                "total_challenges": 1,
                "solved_challenges": 0,
                "challenges": [
                    {
                        "title": "multi",
                        "code": "c2",
                        "difficulty": "hard",
                        "description": "pivot internal foothold track3",
                        "level": 2,
                        "flag_count": 0,
                        "flag_got_count": 0,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

    store = ChallengeStore(HighTrackContestClient(), HighTrackStateStore())

    snapshot = await store.refresh()
    challenge = snapshot.challenges[0]

    assert store.is_effectively_completed(challenge) is False


@pytest.mark.anyio
async def test_challenge_store_clears_stale_local_completion_after_official_reset() -> None:
    class ResetStateStore(DummyStateStore):
        def __init__(self) -> None:
            super().__init__()
            self.flags = {"c2": ["flag{old}"]}
            self.latest_at = {"c2": 0.0}
            self.cleared = []

        def list_submitted_flags(self, challenge_code: str) -> list[str]:
            return list(self.flags.get(challenge_code, []))

        def latest_submitted_flag_at(self, challenge_code: str):
            return self.latest_at.get(challenge_code)

        def clear_submitted_flags(self, challenge_code: str) -> int:
            count = len(self.flags.get(challenge_code, []))
            self.flags[challenge_code] = []
            self.cleared.append(challenge_code)
            return count

        def add_history_event(self, challenge_code: str, event_type: str, payload: str) -> None:
            self.history.append({"event_type": event_type, "payload": payload, "created_at": "now"})

    class ResetContestClient(DummyContestClient):
        async def list_challenges(self):
            return {
                "current_level": 2,
                "total_challenges": 2,
                "solved_challenges": 0,
                "challenges": [
                    {
                        "title": "done",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "finished one",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    },
                    {
                        "title": "todo",
                        "code": "c2",
                        "difficulty": "medium",
                        "description": "open target",
                        "level": 2,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": ["127.0.0.1:8080"],
                    },
                ],
            }

    state = ResetStateStore()
    store = ChallengeStore(ResetContestClient(), state, official_completion_grace_seconds=30)

    snapshot = await store.refresh()

    assert state.cleared == ["c2"]
    assert store.next_candidate(snapshot).code == "c2"
    assert any(item["event_type"] == "official_reset_detected" for item in state.history)
