from __future__ import annotations

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
        "Hints are expensive: only view a hint if there has been no meaningful progress or result for more than 5 minutes. "
        "If the latest snapshot shows the assigned challenge is missing, already completed, or no longer dispatchable, stop stale exploitation immediately, persist a concise provisional_findings note, and switch to state reconciliation. "
        "Never start a guessed or historical challenge code; only start the currently assigned unsolved challenge after re-checking the latest snapshot. "
        "If start_challenge reports already_completed, unlock-level mismatch, or current_level mismatch, refresh once, remap the objective, and do not retry the stale start request. "
        "If a target becomes unreachable or repeatedly times out, do at most 2 short verification probes, record target_unreachable, and stop wasting turns on repeated curl or sleep loops. "
        "If notes contain provisional_findings, treat them as the highest-priority hypotheses before doing generic enumeration. "
        "When a new current_level is unlocked, prioritize challenges at that level before revisiting older levels. "
        "In competition mode, keep worker slots saturated up to the 3-worker limit with unfinished non-paused challenges; if no fresh challenge exists, reuse deferred unfinished challenges instead of leaving slots idle. "
        "Prefer fast, focused probes over slow exhaustive scanning. Do not default to long-running tools such as broad nmap scans when quicker route, API, file, or workflow checks can localize the vulnerability faster."
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
        "Prefer quick endpoint checks, direct exploit validation, and narrow content discovery before any slow port or service scan."
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
        "Decide whether the current situation justifies viewing a hint. "
        "Only do so when repeated progress stalls and no stronger next action exists. "
        "Do not view a hint unless there has been more than 5 minutes without meaningful progress or result."
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
) -> str:
    snapshot_text = ""
    if snapshot is not None:
        snapshot_text = (
            f"Current level: {snapshot.current_level}\n"
            f"Visible challenges: {snapshot.total_challenges}\n"
            f"Solved challenges: {snapshot.solved_challenges}\n"
        )
    active_text = ""
    if active is not None:
        active_text = (
            f"Active challenge: {active.code}\n"
            f"Title: {active.title}\n"
            f"Description: {active.description}\n"
            f"Difficulty: {active.difficulty}\n"
            f"Entrypoints: {active.entrypoints}\n"
        )
    stage_text = f"Current stage: {stage}" if stage else ""
    runtime_text = f"Runtime state: {runtime_state}" if runtime_state else ""
    notes_text = f"Recovered notes: {notes}" if notes else ""
    operator_hints = derive_operator_hints(active, notes)
    operator_hint_text = (
        "Operator hints:\n" + "\n".join(f"- {hint}" for hint in operator_hints)
        if operator_hints
        else ""
    )
    track_profile = TRACK_PROFILES.get(track) if track else None
    track_text = ""
    if track_profile is not None:
        track_text = (
            f"Track: {track_profile.track_id} / {track_profile.name}\n"
            f"Focus: {track_profile.focus}\n"
            "Track priorities:\n"
            + "\n".join(f"- {item}" for item in track_profile.priorities)
        )
    skill_text = "\n".join(
        f"- {skill.name}: {skill.description} | guidance: {skill.usage_guidance}" for skill in skills
    )
    available_skills_text = f"Available skills catalog:\n{available_skills}" if available_skills else ""
    operator_resources_text = f"Operator resources:\n{operator_resources}" if operator_resources else ""
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
    completion_text = ""
    if snapshot is not None and snapshot.total_challenges and snapshot.solved_challenges == snapshot.total_challenges:
        completion_text = (
            "All visible challenges are currently marked completed. "
            "Unless the user explicitly asks to retest or reopen a target, do not perform more exploitation. "
            "Prefer summarizing from the current snapshot, history, and notes."
        )
    summary_text = (
        "The current user request is a summary/final-answer style request. "
        "Prefer concise synthesis over more probing unless a critical fact is missing."
        if summary_request
        else ""
    )
    return "\n\n".join(
        part
        for part in (
            ENTRY_PROMPT.body,
            mode_text,
            completion_text,
            summary_text,
            stage_text,
            runtime_text,
            notes_text,
            operator_hint_text,
            track_text,
            available_skills_text,
            operator_resources_text,
            snapshot_text.strip(),
            active_text.strip(),
            f"Selected skills:\n{skill_text}" if skill_text else "",
        )
        if part
    )


def build_trigger_prompt(trigger: TriggerPrompt) -> str:
    return trigger.body
