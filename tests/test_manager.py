from types import SimpleNamespace

from niuniu_agent.runtime.manager import (
    has_unstarted_dispatchable_challenges,
    partition_dispatchable_challenges,
)


class DummyStateStore:
    def __init__(self, notes_map, runtime_map=None, submitted_flags_map=None):
        self.notes_map = notes_map
        self.runtime_map = runtime_map or {}
        self.submitted_flags_map = submitted_flags_map or {}

    def get_challenge_notes(self, code: str):
        return self.notes_map.get(code, {})

    def list_submitted_flags(self, code: str):
        return self.submitted_flags_map.get(code, [])

    def get_challenge_runtime_state(self, code: str):
        return self.runtime_map.get(code, {})


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


def test_partition_dispatchable_challenges_excludes_deferred_items() -> None:
    snapshot = SimpleNamespace(
        challenges=[
            SimpleNamespace(code="c1", completed=False, flag_count=1),
            SimpleNamespace(code="c2", completed=False, flag_count=1),
        ]
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={"c2": {"defer_until": 200.0}},
        ),
        now=100.0,
    )

    assert dispatchable == ["c1"]
    assert paused == []


def test_partition_dispatchable_challenges_deprioritizes_expired_deferred_items() -> None:
    snapshot = SimpleNamespace(
        challenges=[
            SimpleNamespace(code="c1", completed=False, flag_count=1, level=0),
            SimpleNamespace(code="c2", completed=False, flag_count=1, level=0),
            SimpleNamespace(code="c3", completed=False, flag_count=1, level=0),
        ]
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {
                "c1": {"deprioritized": "true"},
            },
            runtime_map={
                "c1": {"attempt_count": 3, "defer_until": 90.0},
                "c2": {"attempt_count": 0},
                "c3": {"attempt_count": 1},
            },
        ),
        now=100.0,
    )

    assert dispatchable == ["c2", "c3", "c1"]
    assert paused == []


def test_partition_dispatchable_challenges_orders_same_level_by_difficulty() -> None:
    snapshot = SimpleNamespace(
        challenges=[
            SimpleNamespace(code="c-hard", completed=False, flag_count=1, level=0, difficulty="hard"),
            SimpleNamespace(code="c-easy", completed=False, flag_count=1, level=0, difficulty="easy"),
            SimpleNamespace(code="c-unknown", completed=False, flag_count=1, level=0, difficulty="unknown"),
            SimpleNamespace(code="c-medium", completed=False, flag_count=1, level=0, difficulty="medium"),
        ]
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "c-hard": {"attempt_count": 0},
                "c-easy": {"attempt_count": 0},
                "c-unknown": {"attempt_count": 0},
                "c-medium": {"attempt_count": 0},
            },
        ),
    )

    assert dispatchable == ["c-easy", "c-medium", "c-hard", "c-unknown"]
    assert paused == []


def test_has_unstarted_dispatchable_challenges_detects_fresh_targets() -> None:
    snapshot = SimpleNamespace(
        challenges=[
            SimpleNamespace(code="c1", completed=False, flag_count=1),
            SimpleNamespace(code="c2", completed=False, flag_count=1),
            SimpleNamespace(code="c3", completed=True, flag_count=1),
        ]
    )

    result = has_unstarted_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "c1": {"attempt_count": 2},
                "c2": {"attempt_count": 0},
            },
        ),
        current_code="c1",
    )

    assert result is True
