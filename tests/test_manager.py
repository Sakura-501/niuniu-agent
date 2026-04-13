from types import SimpleNamespace

from niuniu_agent.runtime.manager import (
    CompetitionManagerAgent,
    build_manager_challenge_roster,
    has_alternative_unfinished_challenges,
    has_unstarted_dispatchable_challenges,
    partition_dispatchable_challenges,
)


class DummyStateStore:
    def __init__(self, notes_map, runtime_map=None, submitted_flags_map=None):
        self.notes_map = notes_map
        self.runtime_map = runtime_map or {}
        self.submitted_flags_map = submitted_flags_map or {}
        self.memories_map = {}

    def get_challenge_notes(self, code: str):
        return self.notes_map.get(code, {})

    def list_submitted_flags(self, code: str):
        return self.submitted_flags_map.get(code, [])

    def get_challenge_runtime_state(self, code: str):
        return self.runtime_map.get(code, {})

    def list_challenge_memories(self, code: str, limit: int = 1):
        return self.memories_map.get(code, [])[:limit]


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


def test_partition_dispatchable_challenges_prioritizes_current_level_over_older_levels() -> None:
    snapshot = SimpleNamespace(
        current_level=1,
        challenges=[
            SimpleNamespace(code="old", completed=False, flag_count=1, level=0, difficulty="easy"),
            SimpleNamespace(code="new", completed=False, flag_count=1, level=1, difficulty="hard"),
        ],
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "old": {"attempt_count": 0},
                "new": {"attempt_count": 0},
            },
        ),
    )

    assert dispatchable == ["new", "old"]
    assert paused == []


def test_partition_dispatchable_challenges_excludes_locked_future_levels() -> None:
    snapshot = SimpleNamespace(
        current_level=0,
        challenges=[
            SimpleNamespace(code="open", completed=False, flag_count=1, level=0, difficulty="easy"),
            SimpleNamespace(code="locked", completed=False, flag_count=1, level=1, difficulty="easy"),
        ],
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "open": {"attempt_count": 0},
                "locked": {"attempt_count": 0},
            },
        ),
    )

    assert dispatchable == ["open"]
    assert paused == []


def test_partition_dispatchable_challenges_uses_deferred_items_to_fill_idle_workers() -> None:
    snapshot = SimpleNamespace(
        current_level=0,
        challenges=[
            SimpleNamespace(code="fresh", completed=False, flag_count=1, level=0, difficulty="easy"),
            SimpleNamespace(code="deferred-one", completed=False, flag_count=1, level=0, difficulty="medium"),
            SimpleNamespace(code="deferred-two", completed=False, flag_count=1, level=0, difficulty="hard"),
        ],
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "fresh": {"attempt_count": 0},
                "deferred-one": {"attempt_count": 2, "defer_until": 200.0},
                "deferred-two": {"attempt_count": 1, "defer_until": 210.0},
            },
        ),
        now=100.0,
        fill_idle_workers=True,
    )

    assert dispatchable == ["fresh", "deferred-one", "deferred-two"]
    assert paused == []


def test_partition_dispatchable_challenges_prefers_current_level_deferred_over_older_level_fresh_when_filling() -> None:
    snapshot = SimpleNamespace(
        current_level=1,
        challenges=[
            SimpleNamespace(code="old-fresh", completed=False, flag_count=1, level=0, difficulty="easy"),
            SimpleNamespace(code="new-deferred", completed=False, flag_count=1, level=1, difficulty="hard"),
        ],
    )

    dispatchable, paused = partition_dispatchable_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "old-fresh": {"attempt_count": 0},
                "new-deferred": {"attempt_count": 1, "defer_until": 200.0},
            },
        ),
        now=100.0,
        fill_idle_workers=True,
    )

    assert dispatchable == ["new-deferred", "old-fresh"]
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


def test_has_alternative_unfinished_challenges_detects_previously_attempted_targets() -> None:
    snapshot = SimpleNamespace(
        current_level=1,
        challenges=[
            SimpleNamespace(code="c1", completed=False, flag_count=1, level=1),
            SimpleNamespace(code="c2", completed=False, flag_count=1, level=1),
        ]
    )

    result = has_alternative_unfinished_challenges(
        snapshot,
        DummyStateStore(
            {},
            runtime_map={
                "c1": {"attempt_count": 2},
                "c2": {"attempt_count": 4},
            },
        ),
        current_code="c1",
    )

    assert result is True


def test_manager_guidance_omits_recursive_shared_findings_from_notes() -> None:
    challenge = SimpleNamespace(
        code="c1",
        title="demo",
        description="demo",
        difficulty="easy",
        entrypoints=["127.0.0.1:8080"],
    )

    guidance = CompetitionManagerAgent._build_guidance(
        challenge,
        runtime_state={"attempt_count": 2, "failure_count": 1},
    )

    assert "Runtime summary" in guidance
    assert "shared_findings" not in guidance


def test_build_manager_challenge_roster_keeps_global_scheduler_facts() -> None:
    snapshot = SimpleNamespace(
        current_level=2,
        challenges=[
            SimpleNamespace(code="c1", completed=False, flag_count=1, level=2, difficulty="hard", instance_status="running", hint_viewed=True),
            SimpleNamespace(code="c2", completed=False, flag_count=1, level=3, difficulty="easy", instance_status="stopped", hint_viewed=False),
        ],
    )

    state = DummyStateStore(
        {"c2": {"operator_pause": "true"}},
        runtime_map={
            "c1": {"attempt_count": 2, "failure_count": 1, "defer_until": None},
            "c2": {"attempt_count": 0, "failure_count": 0, "defer_until": 200.0},
        },
    )
    state.memories_map = {"c1": [{"memory_type": "turn_summary", "content": "x"}]}

    def list_memories(code: str, limit: int = 1):
        return state.memories_map.get(code, [])[:limit]

    state.list_challenge_memories = list_memories

    roster = build_manager_challenge_roster(snapshot, state)

    assert roster[0]["code"] == "c1"
    assert roster[0]["level"] == 2
    assert roster[0]["instance_status"] == "running"
    assert roster[0]["has_memories"] is True
    assert roster[1]["locked"] is True
    assert roster[1]["paused"] is True
