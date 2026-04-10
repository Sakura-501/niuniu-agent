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
        "at most 3 challenge instances may run at the same time; before starting a challenge instance, check how many are already running. "
        "If a correct flag is submitted and the challenge is shown as completed, stop that challenge instance immediately. "
        "Once one challenge is completed, continue directly to the next unfinished challenge without lingering. "
        "Hints are expensive: only view a hint if there has been no meaningful progress or result for more than 5 minutes."
    ),
)

CHALLENGE_TAKEOVER_PROMPT = TriggerPrompt(
    name="challenge_takeover",
    body=(
        "A challenge is being actively taken over. "
        "First identify the most relevant capability skills, then choose the least wasteful next action. "
        "Before starting any new instance, inspect the currently running challenge count and stay within the 3-instance limit."
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
        "Summarize what was learned, choose the next skill, and continue without restarting from scratch."
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


def build_entry_prompt(
    mode: str,
    snapshot: ContestSnapshot | None,
    active: ChallengeSnapshot | None,
    skills: list,
    stage: str | None = None,
    runtime_state: dict | None = None,
    notes: dict | None = None,
    summary_request: bool = False,
    track: str | None = None,
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
    mode_text = (
        "Mode: competition. Keep running forever and recover from errors."
        if mode == "competition"
        else (
            "Mode: debug. Explain your reasoning and keep responses concise. "
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
            track_text,
            snapshot_text.strip(),
            active_text.strip(),
            f"Selected skills:\n{skill_text}" if skill_text else "",
        )
        if part
    )


def build_trigger_prompt(trigger: TriggerPrompt) -> str:
    return trigger.body
