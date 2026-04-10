from __future__ import annotations

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot


def build_system_prompt(mode: str, snapshot: ContestSnapshot | None, active: ChallengeSnapshot | None) -> str:
    summary = ""
    if snapshot is not None:
        summary = (
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

    if mode == "competition":
        extra = (
            "You are an autonomous pentest agent in nonstop competition mode. "
            "Keep working, keep testing, keep submitting flags, and do not stop because of uncertainty or errors. "
            "If a tool succeeds, continue. If a tool fails, adapt and keep going."
        )
    else:
        extra = (
            "You are an interactive pentest debugging agent. "
            "Explain what you are doing, keep track of completed challenges, and use tools to gather concrete evidence."
        )

    return (
        f"{extra}\n\n"
        f"{summary}"
        f"{active_text}"
        "Only stop when you have no more tool calls to make for the current response."
    )
