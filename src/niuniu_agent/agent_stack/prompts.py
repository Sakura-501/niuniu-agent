from __future__ import annotations

import json
from dataclasses import dataclass

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot
from niuniu_agent.skills.tracks import TRACK_PROFILES


@dataclass(frozen=True, slots=True)
class TriggerPrompt:
    name: str
    body: str


ENTRY_PROMPT = TriggerPrompt(
    name="entry",
    body=(
        "You are the main pentest agent. "
        "Always start from the latest challenge snapshot and keep track of what is completed. "
        "Use tools to gather evidence. "
        "Only stop your current response when you have no more tool calls to make. "
        "You must respect these hard rules: "
        "before starting any challenge instance, first check whether that challenge is already solved or completed; only unsolved challenges may be started. "
        "at most 3 challenge instances may run at the same time; before starting a challenge instance, check how many are already running. "
        "If a correct flag is submitted and the challenge is shown as completed, stop that challenge instance immediately. "
        "Once one challenge is completed, continue directly to the next unfinished challenge without lingering. "
        "View a hint immediately after taking over a challenge if it has not already been viewed. "
        "If the latest snapshot shows the assigned challenge is missing, already completed, or no longer dispatchable, stop stale exploitation immediately, persist a concise provisional_findings note, and switch to state reconciliation. "
        "Never start a guessed or historical challenge code; only start the currently assigned unsolved challenge after re-checking the latest snapshot. "
        "If start_challenge reports already_completed, unlock-level mismatch, or current_level mismatch, refresh once, remap the objective, and do not retry the stale start request. "
        "If a target becomes unreachable or repeatedly times out, do at most 2 short verification probes, record target_unreachable, and stop wasting turns on repeated curl or sleep loops. "
        "If notes contain provisional_findings, treat them as the highest-priority hypotheses before doing generic enumeration. "
        "When a new current_level is unlocked, prioritize challenges at that level before revisiting older levels. "
        "In competition mode, keep worker slots saturated up to the 3-worker limit with unfinished non-paused challenges; if no fresh challenge exists, reuse deferred unfinished challenges instead of leaving slots idle. "
        "Prefer fast, focused probes over slow exhaustive scanning. Do not default to long-running tools such as broad nmap scans when quicker route, API, file, or workflow checks can localize the vulnerability faster."
        " For internal service or vulnerability scanning, prefer fscan first; only fall back to nmap, rustscan, or broader tooling when fscan is not suitable or did not answer the hypothesis."
        " If you have no viable hypothesis, you may try the model's built-in internet search capability for public vulnerability context; if the model reports that network search is unavailable, fall back immediately to local notes, skills, helper scripts, and direct target evidence instead of stalling."
        " Local exploit references and PoC notes may exist under /root/niuniu-agent/exp on the debug machine; check that directory before reinventing public exploit research."
        " When a target must call back, use the public callback host 129.211.15.16 unless a more specific runtime reminder overrides it."
    ),
)

CHALLENGE_TAKEOVER_PROMPT = TriggerPrompt(
    name="challenge_takeover",
    body=(
        "A challenge is being actively taken over. "
        "First identify the most relevant capability skills, then choose the least wasteful next action. "
        "Before starting any instance, verify from the latest challenge snapshot that the target challenge is not already solved. "
        "Before starting any new instance, inspect the currently running challenge count and stay within the 3-instance limit. "
        "Validate existing hypotheses from notes or provisional_findings before broad recon. "
        "Do not use long sleep commands as a default recovery action. "
        "Prefer quick endpoint checks, direct exploit validation, and narrow content discovery before any slow port or service scan. "
        "When an internal host or mixed service surface must be scanned, choose fscan before nmap."
    ),
)

RECON_COMPLETE_PROMPT = TriggerPrompt(
    name="recon_complete",
    body=(
        "Reconnaissance is complete enough to act. "
        "Now decide whether to escalate into exploitation, continue recon, or switch skills."
    ),
)

PRE_EXPLOIT_PROMPT = TriggerPrompt(
    name="pre_exploit",
    body=(
        "You are about to exploit a likely vulnerability. "
        "Prefer the most deterministic path, preserve reproducible evidence, and submit flags immediately if found. "
        "If the challenge becomes completed after flag submission, close its instance immediately and move on."
    ),
)

RECOVERY_PROMPT = TriggerPrompt(
    name="recovery",
    body=(
        "A prior attempt failed or stalled. "
        "Summarize what was learned, choose the next skill, and continue without restarting from scratch. "
        "If the environment changed or the target disappeared, preserve only the reusable clues and stop probing stale entrypoints."
    ),
)

HINT_DECISION_PROMPT = TriggerPrompt(
    name="hint_decision",
    body=(
        "If the challenge hint has not been viewed yet, view it immediately and fold the result into the next exploit plan."
    ),
)

FLAG_SUBMIT_PROMPT = TriggerPrompt(
    name="flag_submit",
    body=(
        "A candidate flag or sensitive artifact may be present. "
        "Validate format, submit immediately, and then continue if more flags may exist. "
        "After a successful submission, verify whether the challenge is now completed and stop its instance immediately if it is."
    ),
)


def derive_operator_hints(active: ChallengeSnapshot | None, notes: dict | None = None) -> list[str]:
    if active is None:
        return []
    notes = notes or {}
    haystack = "\n".join(str(value) for value in notes.values()).lower()
    hints: list[str] = []

    if any(marker in haystack for marker in ("no longer includes challenge", "all demo challenges", "state reconciliation")):
        hints.append(
            "The latest snapshot may be stale or reset. Reconcile state first and avoid exploiting stale challenge codes or entrypoints."
        )
    if any(marker in haystack for marker in ("dify", "127.0.0.1:5001", "/console/api", "createServerReference".lower())):
        hints.append(
            "Treat this as a Dify/Next.js frontend to a loopback-bound backend. Prioritize same-origin route handlers, RSC/server actions, and install/init/signin flows over direct 5001 probing."
        )
        hints.append(
            "Do not burn turns on generic package installs or broad CVE hunting unless a concrete version-linked path appears in the shipped frontend code."
        )
    if any(marker in haystack for marker in ("gradio", "/config", "fn_index", "/run/predict", "api_name=", "/run/flag", "/run/lambda")):
        hints.append(
            "Treat this as a Gradio API challenge. Work from /config to backend function mapping, then exercise api_name/fn_index/state transitions directly with crafted session_hash values."
        )
        hints.append(
            "Avoid local environment setup unless it directly helps decode an observed Gradio protocol artifact; the exposed HTTP API should be the main attack surface."
        )
    if any(marker in haystack for marker in ("telnetd", "login incorrect", "port 23", "telnet")):
        hints.append(
            "Treat brute-force hits as untrusted until confirmed with a protocol-aware telnet client. Respect telnet negotiation and avoid blind retries after repeated connection refusals."
        )
        hints.append(
            "If the service becomes unreachable after login attempts, restart the instance and switch from password spraying to credential-source discovery."
        )
    if any(marker in haystack for marker in ("jwt header kid", "dot-notation", "migration notes", "rule execution")):
        hints.append(
            "Prioritize the migration-notes, JWT kid, and dotted-parameter rule-engine chain before generic enumeration. This looks like an auth-to-admin-to-rule-exec path."
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            deduped.append(hint)
    return deduped


def build_entry_prompt(
    mode: str,
    snapshot: ContestSnapshot | None,
    active: ChallengeSnapshot | None,
    skills: list,
    available_skills: str | None = None,
    stage: str | None = None,
    runtime_state: dict | None = None,
    notes: dict | None = None,
    summary_request: bool = False,
    track: str | None = None,
    operator_resources: dict | None = None,
    hint_context: dict[str, object] | None = None,
) -> str:
    mode_text = (
        "Mode: competition. Keep running forever and recover from errors. "
        "Use the load_skill tool when a task needs specialized instructions before acting."
        if mode == "competition"
        else (
            "Mode: debug. Explain your reasoning and keep responses concise. "
            "Use the load_skill tool when a task needs specialized instructions before acting. "
            "If the user asks for a solution, summary, exploit path, or flag, "
            "format the final answer with clear markdown sections: 结论, 解法, 关键证据, Flag, 下一步."
        )
    )
    fixed_worker_context = (
        "Persistent challenge context for this worker. "
        "Treat this block as durable system context for the entire worker session and keep using it even after history compaction.\n"
        "<worker-static-context>\n"
        + json.dumps(
            {
                "active_challenge": (
                    {
                        "code": active.code,
                        "title": active.title,
                        "difficulty": active.difficulty,
                        "level": active.level,
                    }
                    if active is not None
                    else None
                ),
                "hint_context": hint_context,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n</worker-static-context>"
        if active is not None and hint_context is not None
        else ""
    )
    return "\n\n".join(
        part
        for part in (
            ENTRY_PROMPT.body,
            mode_text,
            fixed_worker_context,
        )
        if part
    )


def build_trigger_prompt(trigger: TriggerPrompt) -> str:
    return trigger.body


def build_runtime_instruction(
    *,
    mode: str,
    user_input: str | None = None,
    snapshot: ContestSnapshot | None = None,
    active: ChallengeSnapshot | None = None,
    runtime_state: dict[str, object] | None = None,
    notes: dict[str, str] | None = None,
    recent_history: list[dict[str, object]] | None = None,
    recent_memories: list[dict[str, object]] | None = None,
    selected_skills: list | None = None,
    available_skills: str | None = None,
    stage: str | None = None,
    track: str | None = None,
    summary_request: bool = False,
    operator_resources: dict | None = None,
    hint_context: dict[str, object] | None = None,
) -> str:
    track_profile = TRACK_PROFILES.get(track) if track else None
    operator_hints = derive_operator_hints(active, notes)
    payload: dict[str, object] = {
        "mode": mode,
        "summary_request": summary_request,
        "snapshot": (
            {
                "current_level": snapshot.current_level,
                "total_challenges": snapshot.total_challenges,
                "solved_challenges": snapshot.solved_challenges,
            }
            if snapshot is not None
            else None
        ),
        "active_challenge": (
            {
                "code": active.code,
                "title": active.title,
                "description": active.description,
                "difficulty": active.difficulty,
                "level": active.level,
                "entrypoints": list(active.entrypoints),
                "hint_viewed": active.hint_viewed,
                "instance_status": active.instance_status,
            }
            if active is not None
            else None
        ),
        "stage": stage,
        "runtime_state": runtime_state or {},
        "notes": notes or {},
        "hint_context": hint_context,
        "recent_history": recent_history or [],
        "recent_memories": recent_memories or [],
        "selected_skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "guidance": skill.usage_guidance,
            }
            for skill in (selected_skills or [])
        ],
        "available_skills_catalog": available_skills or "",
        "track": (
            {
                "track_id": track_profile.track_id,
                "name": track_profile.name,
                "focus": track_profile.focus,
                "priorities": list(track_profile.priorities),
            }
            if track_profile is not None
            else None
        ),
        "operator_hints": operator_hints,
        "operator_resources": operator_resources or {},
    }
    parts: list[str] = []
    if user_input:
        parts.append(user_input)
    parts.append(
        "<system-reminder>\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n</system-reminder>"
    )
    return "\n\n".join(parts)


def build_worker_runtime_instruction(
    *,
    active: ChallengeSnapshot,
    current_level: int | None = None,
    runtime_state: dict[str, object] | None = None,
    notes: dict[str, str] | None = None,
    recent_history: list[dict[str, object]] | None = None,
    recent_memories: list[dict[str, object]] | None = None,
    selected_skills: list | None = None,
    stage: str | None = None,
    track: str | None = None,
    operator_resources: dict | None = None,
    hint_context: dict[str, object] | None = None,
) -> str:
    track_profile = TRACK_PROFILES.get(track) if track else None
    operator_hints = derive_operator_hints(active, notes)
    payload: dict[str, object] = {
        "mode": "competition",
        "current_level": current_level,
        "active_challenge": {
            "code": active.code,
            "title": active.title,
            "description": active.description,
            "difficulty": active.difficulty,
            "level": active.level,
            "entrypoints": list(active.entrypoints),
            "hint_viewed": active.hint_viewed,
            "instance_status": active.instance_status,
        },
        "stage": stage,
        "runtime_state": runtime_state or {},
        "notes": notes or {},
        "hint_context": hint_context,
        "recent_history": recent_history or [],
        "recent_memories": recent_memories or [],
        "selected_skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "guidance": skill.usage_guidance,
            }
            for skill in (selected_skills or [])
        ],
        "track": (
            {
                "track_id": track_profile.track_id,
                "name": track_profile.name,
                "focus": track_profile.focus,
                "priorities": list(track_profile.priorities),
            }
            if track_profile is not None
            else None
        ),
        "operator_hints": operator_hints,
        "operator_resources": operator_resources or {},
    }
    return (
        "<system-reminder>\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n</system-reminder>"
    )
