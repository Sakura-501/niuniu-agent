from niuniu_agent.skills.registry import SkillRegistry


def test_skill_registry_selects_generic_capabilities() -> None:
    registry = SkillRegistry()

    selected = registry.select("web portal login with token api", track="track1")
    names = {skill.name for skill in selected}

    assert "recon_web" in names
    assert "exploit_api" in names
    assert "flag_submit_recovery" in names
