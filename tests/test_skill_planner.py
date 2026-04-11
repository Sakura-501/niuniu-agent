from niuniu_agent.runtime.recovery import extract_runtime_notes, should_view_hint
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
    assert plan.skills[0].name in {"pivot_lateral", "privesc_maintain", "domain_enum"}


def test_plan_skills_respects_track_priority() -> None:
    registry = SkillRegistry()

    plan = plan_skills(
        registry,
        "cloud metadata ai model service",
        runtime_state={"failure_count": 0},
        notes={},
        track="track2",
    )

    assert plan.skills[0].name in {"cve_mapping", "cloud_ai_surface"}


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
    assert any("attack surface" in skill.body.lower() for skill in plan.skills if skill.name == "recon_web")


def test_extract_runtime_notes_captures_foothold_and_summary() -> None:
    notes = extract_runtime_notes("uid=1000(www-data) gid=1000 shell established", [])

    assert "foothold" in notes
    assert "last_summary" in notes


def test_should_view_hint_only_after_repeated_failures() -> None:
    assert should_view_hint(2, False, {}, seconds_since_progress=999) is False
    assert should_view_hint(3, False, {}, seconds_since_progress=120) is False
    assert should_view_hint(3, False, {}, seconds_since_progress=301) is True
    assert should_view_hint(5, True, {}, seconds_since_progress=999) is False
    assert should_view_hint(5, False, {"hint_viewed": "true"}, seconds_since_progress=999) is False
