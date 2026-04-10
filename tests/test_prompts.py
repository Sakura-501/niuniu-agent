from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    build_entry_prompt,
    build_trigger_prompt,
)
from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot
from niuniu_agent.skills.registry import SkillRegistry


def test_entry_prompt_includes_selected_skills() -> None:
    registry = SkillRegistry()
    skills = registry.select("web portal login", track="track1")
    snapshot = ContestSnapshot(current_level=1, total_challenges=2, solved_challenges=0, challenges=[])
    active = ChallengeSnapshot(
        code="c1",
        title="demo",
        description="web portal login",
        difficulty="easy",
        level=1,
    )

    prompt = build_entry_prompt("debug", snapshot, active, skills)

    assert "Selected skills" in prompt
    assert "recon_web" in prompt


def test_entry_prompt_biases_summary_when_requested() -> None:
    prompt = build_entry_prompt(
        "debug",
        ContestSnapshot(current_level=1, total_challenges=1, solved_challenges=1, challenges=[]),
        None,
        [],
        summary_request=True,
    )

    assert "summary/final-answer style request" in prompt
    assert "All visible challenges are currently marked completed" in prompt


def test_trigger_prompt_returns_body() -> None:
    assert "taken over" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)


def test_entry_prompt_contains_instance_and_hint_rules() -> None:
    prompt = build_entry_prompt("competition", None, None, [])

    assert "at most 3 challenge instances" in prompt
    assert "stop that challenge instance immediately" in prompt
    assert "more than 5 minutes" in prompt
