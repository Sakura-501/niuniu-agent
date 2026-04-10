from __future__ import annotations

from dataclasses import dataclass

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot


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
        "Only stop your current response when you have no more tool calls to make."
    ),
)

CHALLENGE_TAKEOVER_PROMPT = TriggerPrompt(
    name="challenge_takeover",
    body=(
        "A challenge is being actively taken over. "
        "First identify the most relevant capability skills, then choose the least wasteful next action."
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
        "Prefer the most deterministic path, preserve reproducible evidence, and submit flags immediately if found."
    ),
)

RECOVERY_PROMPT = TriggerPrompt(
    name="recovery",
    body=(
        "A prior attempt failed or stalled. "
        "Summarize what was learned, choose the next skill, and continue without restarting from scratch."
    ),
)

HINT_DECISION_PROMPT = TriggerPrompt(
    name="hint_decision",
    body=(
        "Decide whether the current situation justifies viewing a hint. "
        "Only do so when repeated progress stalls and no stronger next action exists."
    ),
)

FLAG_SUBMIT_PROMPT = TriggerPrompt(
    name="flag_submit",
    body=(
        "A candidate flag or sensitive artifact may be present. "
        "Validate format, submit immediately, and then continue if more flags may exist."
    ),
)


def build_entry_prompt(
    mode: str,
    snapshot: ContestSnapshot | None,
    active: ChallengeSnapshot | None,
    skills: list,
    stage: str | None = None,
    runtime_state: dict | None = None,
    notes: dict | None = None,
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
    skill_text = "\n".join(
        f"- {skill.name}: {skill.description} | guidance: {skill.usage_guidance}" for skill in skills
    )
    mode_text = (
        "Mode: competition. Keep running forever and recover from errors."
        if mode == "competition"
        else "Mode: debug. Explain your reasoning and keep responses concise."
    )
    return "\n\n".join(
        part
        for part in (
            ENTRY_PROMPT.body,
            mode_text,
            stage_text,
            runtime_text,
            notes_text,
            snapshot_text.strip(),
            active_text.strip(),
            f"Selected skills:\n{skill_text}" if skill_text else "",
        )
        if part
    )


def build_trigger_prompt(trigger: TriggerPrompt) -> str:
    return trigger.body
