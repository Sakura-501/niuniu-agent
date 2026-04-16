from niuniu_agent.runtime.recovery import extract_runtime_notes, persist_critical_challenge_notes, should_view_hint
from niuniu_agent.skills.planner import plan_skills
from niuniu_agent.skills.registry import SkillRegistry


def test_plan_skills_prefers_post_exploit_when_foothold_exists() -> None:
    registry = SkillRegistry()

    plan = plan_skills(
        registry,
        "internal domain host",
        runtime_state={"failure_count": 0},
        notes={"foothold": "www-data shell"},
    )

    assert plan.stage == "post_exploit"
    assert plan.skills[0].name in {"lateral-movement-planning", "privilege-path-analysis", "directory-identity-enumeration"}


def test_plan_skills_respects_track_priority() -> None:
    registry = SkillRegistry()

    plan = plan_skills(
        registry,
        "cloud metadata ai model service",
        runtime_state={"failure_count": 0},
        notes={},
        track="track2",
    )

    assert plan.skills[0].name in {"known-vulnerability-mapping", "cloud-asset-assessment"}


def test_plan_skills_loads_disk_backed_skill_metadata() -> None:
    registry = SkillRegistry()

    plan = plan_skills(
        registry,
        "web portal admin login token api",
        runtime_state={"failure_count": 0},
        notes={},
        track="track1",
    )

    assert any(skill.path.name == "SKILL.md" for skill in plan.skills)
    assert any("attack surface" in skill.body.lower() for skill in plan.skills if skill.name == "web-surface-mapping")


def test_plan_skills_can_select_new_pentest_flow_skills() -> None:
    registry = SkillRegistry()

    plan = plan_skills(
        registry,
        "target ip only, need first pass triage, then pivot to internal service and hunt credentials and flag",
        runtime_state={"failure_count": 0},
        notes={"foothold": "www-data shell"},
        track="track3",
    )

    selected = {skill.name for skill in plan.skills}

    assert "pentest-entrypoint-triage" in selected
    assert "internal-pivot-flow" in selected
    assert "credential-secret-hunting" in selected
    assert "flag-discovery-and-submission" in selected


def test_extract_runtime_notes_captures_foothold_and_summary() -> None:
    notes = extract_runtime_notes("uid=1000(www-data) gid=1000 shell established", [])

    assert "foothold" in notes
    assert "last_summary" in notes


def test_extract_runtime_notes_does_not_treat_flag_as_credential_hint() -> None:
    notes = extract_runtime_notes("found flag{demo-value} and nothing credential-like", [])

    assert "credential_hint" not in notes


def test_should_view_hint_immediately_when_not_yet_viewed() -> None:
    assert should_view_hint(0, False, {}, seconds_since_progress=None, seconds_since_attempt=0) is True
    assert should_view_hint(0, False, {"provisional_findings": "have a lead"}, seconds_since_progress=None, seconds_since_attempt=999) is True
    assert should_view_hint(5, True, {}, seconds_since_progress=None, seconds_since_attempt=999) is False
    assert should_view_hint(5, False, {"hint_viewed": "true"}, seconds_since_progress=None, seconds_since_attempt=999) is False


def test_persist_critical_challenge_notes_promotes_track34_notes_to_persistent_memory(tmp_path) -> None:
    from types import SimpleNamespace

    from niuniu_agent.state_store import StateStore

    store = StateStore(tmp_path / "state.db")
    challenge = SimpleNamespace(code="c1", level=2, description="internal pivot target")

    persist_critical_challenge_notes(
        state_store=store,
        challenge=challenge,
        notes={
            "provisional_findings": "use proxy.php first",
            "target_unreachable": "timed out twice",
        },
    )

    memories = store.list_challenge_memories("c1", limit=10)

    assert any(item["memory_type"] == "persistent_provisional_findings" and item["persistent"] is True for item in memories)
    assert any(item["memory_type"] == "persistent_target_unreachable" and item["persistent"] is True for item in memories)
