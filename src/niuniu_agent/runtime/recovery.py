from __future__ import annotations

import re
from typing import Any


def extract_runtime_notes(output: str, tool_events: list[dict[str, Any]] | None = None) -> dict[str, str]:
    notes: dict[str, str] = {}
    text = output or ""

    foothold_patterns = [
        r"\bwww-data\b.*\bshell\b",
        r"\broot\b.*\bshell\b",
        r"\buid=\d+\b.*",
        r"\bAdministrator\b.*",
    ]
    for pattern in foothold_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            notes["foothold"] = match.group(0)[:500]
            break

    credential_patterns = [
        r"password\s*[:=]\s*([^\s]+)",
        r"token\s*[:=]\s*([^\s]+)",
        r"flag\{[^}\n]+\}",
    ]
    for pattern in credential_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            notes["credential_hint"] = match.group(0)[:500]
            break

    if tool_events:
        notes["last_tool_count"] = str(len(tool_events))

    if text:
        notes["last_summary"] = text[:1000]
    return notes


def should_view_hint(
    failure_count: int,
    challenge_hint_viewed: bool,
    notes: dict[str, str] | None = None,
    seconds_since_progress: float | None = None,
    seconds_since_attempt: float | None = None,
) -> bool:
    notes = notes or {}
    if challenge_hint_viewed:
        return False
    if notes.get("hint_viewed") == "true":
        return False
    return True


def recover_competition_state(
    *,
    snapshot: Any,
    state_store: Any,
    competition_run_id: str,
) -> dict[str, object]:
    normalized_completed: list[str] = []
    reset_stale_active_challenges: list[str] = []
    removed_stale_agents: list[str] = []

    for challenge in snapshot.challenges:
        local_flags = state_store.list_submitted_flags(challenge.code)
        effective_completed = bool(challenge.completed) or (
            getattr(challenge, "flag_count", 0) > 0 and len(local_flags) >= getattr(challenge, "flag_count", 0)
        ) or (getattr(challenge, "flag_count", 0) == 0 and bool(local_flags))
        if effective_completed:
            runtime_state = state_store.get_challenge_runtime_state(challenge.code)
            if runtime_state.get("active") or runtime_state.get("failure_count", 0):
                state_store.record_challenge_success(challenge.code)
                normalized_completed.append(challenge.code)
            continue
        runtime_state = state_store.get_challenge_runtime_state(challenge.code)
        if runtime_state.get("active"):
            state_store.clear_active_challenge(challenge.code)
            if hasattr(state_store, "add_history_event"):
                state_store.add_history_event(
                    challenge.code,
                    "stale_attempt_reset",
                    "cleared stale active challenge attempt during competition recovery",
                )
            reset_stale_active_challenges.append(challenge.code)

    for agent in state_store.list_agent_statuses():
        role = agent.get("role")
        metadata = dict(agent.get("metadata") or {})
        agent_id = str(agent["agent_id"])
        if role == "manager":
            run_id = str(metadata.get("run_id") or "").strip()
            if run_id and run_id != competition_run_id:
                state_store.delete_agent_status(agent_id)
                removed_stale_agents.append(agent_id)
        elif role == "challenge_worker":
            worker_run_id = str(metadata.get("competition_run_id") or "").strip()
            if worker_run_id and worker_run_id != competition_run_id and agent.get("status") != "completed":
                challenge_code = str(agent.get("challenge_code") or "").strip()
                if challenge_code:
                    runtime_state = state_store.get_challenge_runtime_state(challenge_code)
                    if runtime_state.get("active"):
                        state_store.clear_active_challenge(challenge_code)
                        if challenge_code not in reset_stale_active_challenges:
                            reset_stale_active_challenges.append(challenge_code)
                        if hasattr(state_store, "add_history_event"):
                            state_store.add_history_event(
                                challenge_code,
                                "stale_attempt_reset",
                                "cleared stale active challenge attempt while removing old-run worker state",
                            )
                state_store.delete_agent_status(agent_id)
                removed_stale_agents.append(agent_id)

    return {
        "normalized_completed_challenges": normalized_completed,
        "reset_stale_active_challenges": reset_stale_active_challenges,
        "removed_stale_agents": removed_stale_agents,
    }
