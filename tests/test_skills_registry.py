from pathlib import Path

from niuniu_agent.skills.registry import SkillRegistry


def test_skill_registry_selects_generic_capabilities() -> None:
    registry = SkillRegistry()

    selected = registry.select("web portal login with token api", track="track1")
    names = {skill.name for skill in selected}

    assert "web-surface-mapping" in names
    assert "api-workflow-testing" in names
    assert "evidence-capture" in names


def test_skill_registry_selects_ai_platform_skills_from_text() -> None:
    registry = SkillRegistry()

    selected = registry.select("self-hosted dify portal with /config gradio fn_index and 127.0.0.1:5001 backend using next.js middleware", track="track2")
    names = {skill.name for skill in selected}

    assert "ai-platform-attack-surface" in names
    assert "dify-self-hosted-assessment" in names
    assert "gradio-api-abuse" in names
    assert "nextjs-middleware-bypass" in names


def test_skill_registry_selects_supply_chain_skills_from_text() -> None:
    registry = SkillRegistry()

    selected = registry.select("package.json github actions dependency confusion private registry requirements.txt", track="track2")
    names = {skill.name for skill in selected}

    assert "supply-chain-poisoning-assessment" in names
    assert "dependency-confusion-assessment" in names
    assert "ci-workflow-poisoning" in names


def test_skill_registry_selects_local_exp_catalog_from_text() -> None:
    registry = SkillRegistry()

    selected = registry.select("need local exploit poc from /root/niuniu-agent/exp for a cve", track="track2")
    names = {skill.name for skill in selected}

    assert "local-exp-catalog" in names


def test_skill_registry_selects_track3_lateral_helpers_from_text() -> None:
    registry = SkillRegistry()

    selected = registry.select("php lfi pearcmd redis mariadb ligolo sshuttle pivot proxy.php sess_ csrf", track="track3")
    names = {skill.name for skill in selected}

    assert "pearcmd-php-shell-drop" in names
    assert "redis-mariadb-lateral-movement" in names
    assert "tool-ligolo-sshuttle" in names
    assert "php-session-hijack-helper" in names
    assert "proxy-php-ssrf-lfi-helper" in names


def test_skill_registry_loads_skill_body_from_disk() -> None:
    registry = SkillRegistry()

    loaded = registry.load_full_text("web-surface-mapping")

    assert "<skill name=\"web-surface-mapping\">" in loaded
    assert "attack surface" in loaded.lower()


def test_skill_registry_describes_available_disk_skills() -> None:
    registry = SkillRegistry()

    description = registry.describe_available()

    assert "web-surface-mapping" in description
    assert "web-vulnerability-testing" in description
    assert "directory-identity-enumeration" in description


def test_skill_registry_can_load_temp_skill_directory(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: sample-skill\n"
        "description: Use when sample token behavior appears in a target workflow.\n"
        "---\n\n"
        "# Sample Skill\n\n"
        "Use this skill when sample token behavior appears.\n",
        encoding="utf-8",
    )

    registry = SkillRegistry(skills_dir=tmp_path / "skills")

    assert registry.load_full_text("sample-skill").startswith("<skill name=\"sample-skill\">")
    assert "Sample Skill" in registry.load_full_text("sample-skill")


def test_all_builtin_skills_use_spec_style_frontmatter() -> None:
    skills_root = Path("/Users/nonoge/Desktop/auto_pentest/niuniu-agent/skills")

    for skill_file in sorted(skills_root.rglob("SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        frontmatter_text = text.split("---", 2)[1].strip()
        frontmatter = frontmatter_text.splitlines()
        keys = [line.split(":", 1)[0].strip() for line in frontmatter if ":" in line]
        assert keys == ["name", "description"], skill_file
        name_value = frontmatter[0].split(":", 1)[1].strip()
        description_value = frontmatter[1].split(":", 1)[1].strip()
        assert "-" in name_value, skill_file
        assert description_value.startswith("Use when"), skill_file
