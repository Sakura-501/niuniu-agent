from types import SimpleNamespace

from niuniu_agent.runtime.manager import partition_dispatchable_challenges


class DummyStateStore:
    def __init__(self, notes_map):
        self.notes_map = notes_map

    def get_challenge_notes(self, code: str):
        return self.notes_map.get(code, {})

    def list_submitted_flags(self, code: str):
        return []


def test_partition_dispatchable_challenges_excludes_paused_items() -> None:
    snapshot = SimpleNamespace(
        challenges=[
            SimpleNamespace(code="c1", completed=False),
            SimpleNamespace(code="c2", completed=False),
            SimpleNamespace(code="c3", completed=True),
        ]
    )
    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore({"c2": {"operator_pause": "true"}}),
    )

    assert dispatchable == ["c1"]
    assert paused == ["c2"]
