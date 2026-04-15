from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    HINT_DECISION_PROMPT,
    RECOVERY_PROMPT,
    build_transient_guidance,
    build_runtime_instruction,
    build_worker_runtime_instruction,
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

    assert "Selected skills" not in prompt
    runtime_instruction = build_runtime_instruction(
        mode="debug",
        user_input="test",
        snapshot=snapshot,
        active=active,
        selected_skills=skills,
    )
    assert "web-surface-mapping" in runtime_instruction


def test_entry_prompt_biases_summary_when_requested() -> None:
    prompt = build_entry_prompt(
        "debug",
        ContestSnapshot(current_level=1, total_challenges=1, solved_challenges=1, challenges=[]),
        None,
        [],
        summary_request=True,
    )

    assert "summary/final-answer style request" not in prompt
    assert "All visible challenges are currently marked completed" not in prompt


def test_trigger_prompt_returns_body() -> None:
    assert "taken over" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)
    assert "likely directories for flag-named files" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)
    assert "runtime/session_logs" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)
    assert "Think deeply about the official hint" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)
    assert "operator_strategy" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)
    assert "before deviating" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)
    assert "previous container instance" in build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT)


def test_build_transient_guidance_serializes_only_enabled_dynamic_directives() -> None:
    prompt = build_transient_guidance([RECOVERY_PROMPT, HINT_DECISION_PROMPT])

    assert "<system-reminder>" in prompt
    assert "transient_directives" in prompt
    assert "A prior attempt failed or stalled" in prompt
    assert "view it immediately" in prompt


def test_entry_prompt_contains_instance_and_hint_rules() -> None:
    prompt = build_entry_prompt("competition", None, None, [])

    assert "first check whether that challenge is already solved or completed" in prompt
    assert "at most 3 challenge instances" in prompt
    assert "stop that challenge instance immediately" in prompt
    assert "View a hint immediately" in prompt
    assert "Do not just read the official hint superficially" in prompt
    assert "missing, already completed, or no longer dispatchable" in prompt
    assert "Never start a guessed or historical challenge code" in prompt
    assert "do at most 2 short verification probes" in prompt
    assert "provisional_findings" in prompt
    assert "prioritize challenges at that level before revisiting older levels" in prompt
    assert "reuse deferred unfinished challenges instead of leaving slots idle" in prompt
    assert "Prefer fast, focused probes over slow exhaustive scanning" in prompt
    assert "broad nmap scans" in prompt
    assert "prefer fscan first" in prompt
    assert "Prefer forward connections, webshell-driven probing" in prompt
    assert "If reverse callback or tunnel setup fails" in prompt
    assert "verify that the listener is actually reachable" in prompt
    assert "require a clear command-output marker" in prompt
    assert "A bare 200 response" in prompt
    assert "Do not default to password brute-force or spraying" in prompt
    assert "compromised service instance is likely to contain at least one flag" in prompt
    assert "search the most likely local service directories for flag-related filenames" in prompt
    assert "flag1, flag2, flag.txt, flag1.txt" in prompt
    assert "noisy global filesystem search" in prompt
    assert "after one flag is submitted successfully, continue deeper" in prompt
    assert "built-in internet search capability" in prompt
    assert "Do not treat runtime/session_logs, local test files, or historical snippets as primary evidence" in prompt
    assert "follow the provided operator strategy as the default attack route" in prompt
    assert "first unresolved operator-strategy step" in prompt
    assert "before deviating from that route" in prompt
    assert "previous container instance" in prompt
    assert "intermediate files" in prompt
    assert "/root/niuniu-agent/exp" in prompt
    assert "129.211.15.16" in prompt
    assert "172.21.0.36" in prompt
    assert "Active challenge:" not in prompt
    assert "Recovered notes:" not in prompt


def test_entry_prompt_can_embed_fixed_worker_hint_context() -> None:
    active = ChallengeSnapshot(
        code="c-fixed",
        title="upload portal",
        description="web upload target",
        difficulty="medium",
        level=2,
    )

    prompt = build_entry_prompt(
        "competition",
        None,
        active,
        [],
        hint_context={
            "hint_viewed": True,
            "hint_content": "后台上传功能的后缀名检测不够全面。",
        },
        operator_strategy="先上传 webshell，再 fscan 扫内网。",
    )

    assert "Persistent challenge context for this worker" in prompt
    assert "hard execution constraints" in prompt
    assert "current run only" in prompt
    assert "c-fixed" in prompt
    assert "后台上传功能的后缀名检测不够全面" in prompt
    assert "先上传 webshell，再 fscan 扫内网。" in prompt


def test_entry_prompt_can_embed_available_skills_catalog_in_fixed_prefix() -> None:
    prompt = build_entry_prompt(
        "competition",
        None,
        None,
        [],
        available_skills="- web-surface-mapping: demo\n- api-workflow-testing: demo",
    )

    assert "Persistent available skills catalog" in prompt
    assert "web-surface-mapping" in prompt
    assert "api-workflow-testing" in prompt


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

    assert "callback_server" not in prompt
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

    prompt = build_runtime_instruction(
        mode="competition",
        active=active,
        notes={"provisional_findings": "config exposed fn_index and /run/predict; Gradio api_name=lambda and /run/Flag are reachable."},
    )

    assert "<system-reminder>" in prompt
    assert "Gradio API challenge" in prompt
    assert "session_hash" in prompt


def test_derive_operator_hints_for_track3_chain_overrides() -> None:
    active = ChallengeSnapshot(
        code="K7kbx40FbhQNODZkS",
        title="layer breach",
        description="web target",
        difficulty="hard",
        level=3,
    )

    hints = derive_operator_hints(
        active,
        {"provisional_findings": "proxy.php SSRF, file:// lfi, webshell already proven"},
    )

    assert any("query/report/export" in hint or "data-query functionality" in hint for hint in hints)
    assert any("Do not brute-force SSH" in hint or "Do not brute-force" in hint for hint in hints)
    assert any("reachable IPs" in hint or "network architecture" in hint for hint in hints)
    assert any("172.21.0.36" in hint for hint in hints)


def test_derive_operator_hints_for_link_violation_prioritizes_upload_and_datastores() -> None:
    active = ChallengeSnapshot(
        code="6RmRST2HkeTbwgbyMJaN",
        title="link violation",
        description="web target",
        difficulty="hard",
        level=3,
    )

    hints = derive_operator_hints(
        active,
        {"provisional_findings": "old noisy session sample only"},
    )

    assert any("upload foothold" in hint or "upload" in hint for hint in hints)
    assert any("network map" in hint or "network segments" in hint for hint in hints)
    assert any("Redis" in hint or "MariaDB" in hint for hint in hints)


def test_derive_operator_hints_for_behind_the_firewall_prioritizes_lfi_chain_and_ssh_validation() -> None:
    active = ChallengeSnapshot(
        code="2ihdUTWqg7iVcvvD7GAZzOadCxS",
        title="behind the firewall",
        description="web target",
        difficulty="hard",
        level=3,
    )

    hints = derive_operator_hints(
        active,
        {"provisional_findings": "tunnel path uncertain"},
    )

    assert any("page-loading" in hint or "frontend/page-loading" in hint for hint in hints)
    assert any("SSH" in hint for hint in hints)
    assert any("129.211.15.16" in hint or "172.21.0.36" in hint for hint in hints)


def test_build_runtime_instruction_omits_available_skills_but_keeps_operator_resources() -> None:
    active = ChallengeSnapshot(
        code="c4",
        title="demo",
        description="demo",
        difficulty="easy",
        level=1,
    )

    prompt = build_runtime_instruction(
        mode="competition",
        active=active,
        available_skills="- web-surface-mapping: demo",
        operator_resources={"callback_server": {"host": "129.211.15.16", "username": "root"}},
    )

    assert "available_skills_catalog" not in prompt
    assert "callback_server" in prompt
    assert "129.211.15.16" in prompt


def test_build_worker_runtime_instruction_omits_fixed_context_duplicates() -> None:
    active = ChallengeSnapshot(
        code="c5",
        title="demo",
        description="demo",
        difficulty="easy",
        level=1,
    )

    prompt = build_worker_runtime_instruction(
        active=active,
        hint_context={"hint_viewed": True, "hint_content": "fixed hint"},
        notes={"last_summary": "demo"},
    )

    assert '"active_challenge"' not in prompt
    assert '"hint_context"' not in prompt
    assert '"notes"' in prompt


def test_build_runtime_instruction_is_stable_for_reordered_dicts() -> None:
    active = ChallengeSnapshot(
        code="c3",
        title="demo",
        description="api target",
        difficulty="easy",
        level=1,
    )

    prompt_a = build_runtime_instruction(
        mode="competition",
        active=active,
        runtime_state={"b": 2, "a": 1},
        notes={"y": "two", "x": "one"},
        operator_resources={"callback_server": {"username": "root", "host": "1.1.1.1"}},
    )
    prompt_b = build_runtime_instruction(
        mode="competition",
        active=active,
        runtime_state={"a": 1, "b": 2},
        notes={"x": "one", "y": "two"},
        operator_resources={"callback_server": {"host": "1.1.1.1", "username": "root"}},
    )

    assert prompt_a == prompt_b
