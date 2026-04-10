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
    def list_submitted_flags(self, challenge_code: str) -> list[str]:
        return ["flag{local}"] if challenge_code == "c2" else []


@pytest.mark.anyio
async def test_challenge_store_refresh_and_next_candidate() -> None:
    store = ChallengeStore(DummyContestClient(), DummyStateStore())

    snapshot = await store.refresh()
    challenge = store.next_candidate(snapshot)

    assert snapshot.current_level == 2
    assert challenge is not None
    assert challenge.code == "c2"
    assert "local_flags=1" in store.render_summary(snapshot)
