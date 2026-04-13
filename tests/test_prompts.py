from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    derive_operator_hints,
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
    assert "web-surface-mapping" in prompt


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

    assert "first check whether that challenge is already solved or completed" in prompt
    assert "at most 3 challenge instances" in prompt
    assert "stop that challenge instance immediately" in prompt
    assert "more than 5 minutes" in prompt
    assert "missing, already completed, or no longer dispatchable" in prompt
    assert "Never start a guessed or historical challenge code" in prompt
    assert "do at most 2 short verification probes" in prompt
    assert "provisional_findings" in prompt
    assert "prioritize challenges at that level before revisiting older levels" in prompt
    assert "reuse deferred unfinished challenges instead of leaving slots idle" in prompt


def test_entry_prompt_includes_callback_resource_when_available() -> None:
    prompt = build_entry_prompt(
        "competition",
        None,
        None,
        [],
        operator_resources={
            "callback_server": {
                "host": "129.211.15.16",
                "username": "root",
                "password": "123QWE@qwe",
                "usage": "Use for reverse shells, pivoting, and persistence.",
            }
        },
    )

    assert "callback_server" in prompt
    assert "129.211.15.16" in prompt


def test_derive_operator_hints_for_dify_style_notes() -> None:
    active = ChallengeSnapshot(
        code="c1",
        title="portal",
        description="dify target",
        difficulty="easy",
        level=1,
    )

    hints = derive_operator_hints(
        active,
        {
            "provisional_findings": "Dify frontend only reachable externally; data-api-prefix=http://127.0.0.1:5001/console/api and direct /console/api returns 404.",
        },
    )

    assert any("loopback-bound backend" in hint for hint in hints)
    assert any("direct 5001 probing" in hint for hint in hints)


def test_entry_prompt_includes_gradio_operator_hints_when_notes_match() -> None:
    active = ChallengeSnapshot(
        code="c2",
        title="gradio demo",
        description="ai challenge",
        difficulty="medium",
        level=2,
    )

    prompt = build_entry_prompt(
        "competition",
        None,
        active,
        [],
        notes={"provisional_findings": "config exposed fn_index and /run/predict; Gradio api_name=lambda and /run/Flag are reachable."},
    )

    assert "Operator hints:" in prompt
    assert "Gradio API challenge" in prompt
    assert "session_hash" in prompt
