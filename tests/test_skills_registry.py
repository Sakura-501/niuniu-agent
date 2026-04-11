from pathlib import Path

from niuniu_agent.skills.registry import SkillRegistry


def test_skill_registry_selects_generic_capabilities() -> None:
    registry = SkillRegistry()

    selected = registry.select("web portal login with token api", track="track1")
    names = {skill.name for skill in selected}

    assert "recon_web" in names
    assert "exploit_api" in names
    assert "flag_submit_recovery" in names


def test_skill_registry_loads_skill_body_from_disk() -> None:
    registry = SkillRegistry()

    loaded = registry.load_full_text("recon_web")

    assert "<skill name=\"recon_web\">" in loaded
    assert "attack surface" in loaded.lower()


def test_skill_registry_describes_available_disk_skills() -> None:
    registry = SkillRegistry()

    description = registry.describe_available()

    assert "recon_web" in description
    assert "exploit_web" in description
    assert "domain_enum" in description


def test_skill_registry_can_load_temp_skill_directory(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: sample_skill\n"
        "description: Sample skill for registry tests\n"
        "trigger_keywords: sample, token\n"
        "recommended_tracks: track1, track2\n"
        "usage_guidance: Prefer deterministic validation first.\n"
        "---\n\n"
        "# Sample Skill\n\n"
        "Use this skill when sample token behavior appears.\n",
        encoding="utf-8",
    )

    registry = SkillRegistry(skills_dir=tmp_path / "skills")
    selected = registry.select("sample token endpoint", track="track1")

    assert [skill.name for skill in selected] == ["sample_skill"]
    assert "Sample Skill" in registry.load_full_text("sample_skill")
