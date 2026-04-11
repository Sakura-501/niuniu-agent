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

    def list_submitted_flags(self, challenge_code: str) -> list[str]:
        return ["flag{local}"] if challenge_code == "c2" else []

    def get_challenge_runtime_state(self, challenge_code: str) -> dict[str, object]:
        return {"active": False, "failure_count": 0, "last_error": None}

    def get_challenge_notes(self, challenge_code: str) -> dict[str, str]:
        return self.notes

    def list_history(self, challenge_code: str, limit: int = 10):
        return self.history[:limit]

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
async def test_challenge_store_autonomous_prompt_includes_history_and_notes() -> None:
    state = DummyStateStore()
    state.history = [{"event_type": "turn_completed", "payload": "summary", "created_at": "now"}]
    state.notes = {"foothold": "user shell"}
    store = ChallengeStore(DummyContestClient(), state)
    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    prompt = store.build_autonomous_prompt(snapshot, challenge)

    assert "turn_completed" in prompt
    assert "foothold" in prompt


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
