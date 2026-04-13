from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from niuniu_agent.control_plane.challenge_store import compact_challenge_notes
from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.coordinator import CompetitionCoordinator
from niuniu_agent.runtime.findings_bus import ChallengeFindingsBus
from niuniu_agent.strategies.local_exp_catalog import has_local_exp_support
from niuniu_agent.skills.tracks import TRACK_PROFILES, infer_track


@dataclass(slots=True)
class CompetitionManagerAgent:
    context: RuntimeContext
    findings_bus: ChallengeFindingsBus
    _last_guidance: dict[str, str] = field(default_factory=dict)

    @property
    def agent_id(self) -> str:
        return self.context.agent_id or "manager:competition"

    def heartbeat(self, snapshot: ContestSnapshot, coordinator: CompetitionCoordinator) -> None:
        dispatchable, paused = partition_dispatchable_challenges(snapshot, self.context.state_store)
        idle_slots = max(0, coordinator.max_parallel_challenges - coordinator.active_count())
        active_workers = [
            {"challenge_code": code, "task_running": coordinator.is_running(code)}
            for code in sorted(coordinator.worker_tasks.keys())
        ]
        summary = (
            f"active_workers={coordinator.active_count()} "
            f"idle_slots={idle_slots} "
            f"dispatchable={len(dispatchable)} paused={len(paused)}"
        )
        metadata = {
            "current_level": snapshot.current_level,
            "pending_challenges": dispatchable,
            "paused_challenges": paused,
            "active_workers": active_workers,
            "idle_slots": idle_slots,
            "challenge_roster": build_manager_challenge_roster(snapshot, self.context.state_store),
            "run_id": self.agent_id.split(":")[-1] if ":" in self.agent_id else None,
        }
        self.context.state_store.upsert_agent_status(
            agent_id=self.agent_id,
            role=self.context.agent_role or "manager",
            challenge_code=None,
            status="running",
            summary=summary,
            metadata=metadata,
        )
        self.context.state_store.append_agent_event(
            agent_id=self.agent_id,
            challenge_code=None,
            event_type="manager_cycle",
            payload=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        )

    async def publish_assignment_guidance(
        self,
        snapshot: ContestSnapshot,
        challenge_codes: list[str],
    ) -> None:
        if not challenge_codes:
            return
        index = {challenge.code: challenge for challenge in snapshot.challenges}
        for code in challenge_codes:
            challenge = index.get(code)
            if challenge is None:
                continue
            guidance = self._build_guidance(
                challenge,
                runtime_state=self.context.state_store.get_challenge_runtime_state(code),
            )
            if self._last_guidance.get(code) == guidance:
                continue
            await self.findings_bus.post(code, source=self.agent_id, content=guidance)
            self.context.state_store.append_agent_event(
                agent_id=self.agent_id,
                challenge_code=code,
                event_type="manager_guidance",
                payload=guidance,
            )
            self._last_guidance[code] = guidance

    def reconcile(self, coordinator: CompetitionCoordinator) -> None:
        for status in self.context.state_store.list_agent_statuses(role="challenge_worker"):
            challenge_code = status.get("challenge_code")
            if not challenge_code or status.get("status") != "running":
                continue
            if coordinator.is_running(str(challenge_code)):
                continue
            metadata = dict(status.get("metadata") or {})
            metadata["recovery_reason"] = "worker task missing from coordinator"
            self.context.state_store.upsert_agent_status(
                agent_id=str(status["agent_id"]),
                role="challenge_worker",
                challenge_code=str(challenge_code),
                status="waiting_recovery",
                summary="worker task missing; waiting for outer loop reschedule",
                metadata=metadata,
                last_error=str(status.get("last_error") or ""),
            )

    @staticmethod
    def _build_guidance(
        challenge: ChallengeSnapshot,
        *,
        runtime_state: dict[str, object] | None = None,
    ) -> str:
        track = infer_track(challenge.description)
        profile = TRACK_PROFILES.get(track)
        priorities = "\n".join(f"- {item}" for item in (profile.priorities if profile else ()))
        runtime_text = json.dumps(runtime_state or {}, ensure_ascii=False, sort_keys=True)[:400]
        return (
            f"Manager guidance for {challenge.code} / {challenge.title}.\n"
            f"Track: {track}\n"
            f"Difficulty: {challenge.difficulty}\n"
            f"Entrypoints: {challenge.entrypoints}\n"
            "Priorities:\n"
            f"{priorities or '- follow the most deterministic next step'}\n"
            f"Runtime summary: {runtime_text or '{}'}"
        )


def build_manager_challenge_roster(
    snapshot: ContestSnapshot | Any,
    state_store: Any,
) -> list[dict[str, object]]:
    roster: list[dict[str, object]] = []
    current_level = getattr(snapshot, "current_level", None)
    for challenge in getattr(snapshot, "challenges", []):
        local_flags = state_store.list_submitted_flags(challenge.code)
        effective_completed = bool(challenge.completed) or (
            getattr(challenge, "flag_count", 0) > 0 and len(local_flags) >= getattr(challenge, "flag_count", 0)
        ) or (getattr(challenge, "flag_count", 0) == 0 and bool(local_flags))
        notes = state_store.get_challenge_notes(challenge.code)
        runtime_state = state_store.get_challenge_runtime_state(challenge.code)
        roster.append(
            {
                "code": challenge.code,
                "level": getattr(challenge, "level", 0),
                "difficulty": getattr(challenge, "difficulty", "unknown"),
                "completed": effective_completed,
                "locked": _challenge_is_locked(challenge, current_level),
                "paused": notes.get("operator_pause") == "true",
                "deferred": runtime_state.get("defer_until") not in (None, ""),
                "attempt_count": int(runtime_state.get("attempt_count", 0) or 0),
                "failure_count": int(runtime_state.get("failure_count", 0) or 0),
                "instance_status": getattr(challenge, "instance_status", None),
                "hint_viewed": getattr(challenge, "hint_viewed", False),
                "has_memories": bool(state_store.list_challenge_memories(challenge.code, limit=1)),
            }
        )
    return roster


def partition_dispatchable_challenges(
    snapshot: ContestSnapshot | Any,
    state_store: Any,
    *,
    now: float | None = None,
    fill_idle_workers: bool = False,
) -> tuple[list[str], list[str]]:
    dispatchable: list[tuple[tuple[int, int, int, int, int, int, int, str], str]] = []
    deferred: list[tuple[tuple[int, int, int, int, int, int, int, str], str]] = []
    paused: list[str] = []
    current = time.time() if now is None else now
    current_level = getattr(snapshot, "current_level", None)
    for challenge in snapshot.challenges:
        local_flags = state_store.list_submitted_flags(challenge.code)
        effective_completed = bool(challenge.completed) or (
            getattr(challenge, "flag_count", 0) > 0 and len(local_flags) >= getattr(challenge, "flag_count", 0)
        ) or (getattr(challenge, "flag_count", 0) == 0 and bool(local_flags))
        if effective_completed:
            continue
        if _challenge_is_locked(challenge, current_level):
            continue
        notes = state_store.get_challenge_notes(challenge.code)
        if notes.get("operator_pause") == "true":
            paused.append(challenge.code)
            continue
        runtime_state = state_store.get_challenge_runtime_state(challenge.code)
        defer_until = runtime_state.get("defer_until")
        is_deferred = defer_until not in (None, "") and float(defer_until) > current
        ranked = (
            (
                _challenge_dispatch_priority(
                    challenge=challenge,
                    runtime_state=runtime_state,
                    notes=notes,
                    current_level=current_level,
                    deferred=is_deferred,
                ),
                challenge.code,
            )
        )
        if is_deferred:
            deferred.append(ranked)
            continue
        dispatchable.append(ranked)
    ranked = dispatchable if not fill_idle_workers else [*dispatchable, *deferred]
    ordered = [code for _priority, code in sorted(ranked)]
    return ordered, paused


def has_unstarted_dispatchable_challenges(
    snapshot: ContestSnapshot | Any,
    state_store: Any,
    *,
    current_code: str,
    now: float | None = None,
) -> bool:
    current = time.time() if now is None else now
    current_level = getattr(snapshot, "current_level", None)
    for challenge in snapshot.challenges:
        if challenge.code == current_code:
            continue
        local_flags = state_store.list_submitted_flags(challenge.code)
        effective_completed = bool(challenge.completed) or (
            getattr(challenge, "flag_count", 0) > 0 and len(local_flags) >= getattr(challenge, "flag_count", 0)
        ) or (getattr(challenge, "flag_count", 0) == 0 and bool(local_flags))
        if effective_completed:
            continue
        if _challenge_is_locked(challenge, current_level):
            continue
        notes = state_store.get_challenge_notes(challenge.code)
        if notes.get("operator_pause") == "true":
            continue
        runtime_state = state_store.get_challenge_runtime_state(challenge.code)
        defer_until = runtime_state.get("defer_until")
        if defer_until not in (None, "") and float(defer_until) > current:
            continue
        if int(runtime_state.get("attempt_count", 0) or 0) == 0:
            return True
    return False


def has_alternative_unfinished_challenges(
    snapshot: ContestSnapshot | Any,
    state_store: Any,
    *,
    current_code: str,
    now: float | None = None,
) -> bool:
    current = time.time() if now is None else now
    current_level = getattr(snapshot, "current_level", None)
    for challenge in snapshot.challenges:
        if challenge.code == current_code:
            continue
        local_flags = state_store.list_submitted_flags(challenge.code)
        effective_completed = bool(challenge.completed) or (
            getattr(challenge, "flag_count", 0) > 0 and len(local_flags) >= getattr(challenge, "flag_count", 0)
        ) or (getattr(challenge, "flag_count", 0) == 0 and bool(local_flags))
        if effective_completed:
            continue
        if _challenge_is_locked(challenge, current_level):
            continue
        notes = state_store.get_challenge_notes(challenge.code)
        if notes.get("operator_pause") == "true":
            continue
        runtime_state = state_store.get_challenge_runtime_state(challenge.code)
        defer_until = runtime_state.get("defer_until")
        if defer_until not in (None, "") and float(defer_until) > current:
            continue
        return True
    return False


def _challenge_dispatch_priority(
    *,
    challenge: ChallengeSnapshot | Any,
    runtime_state: dict[str, object],
    notes: dict[str, str],
    current_level: int | None,
    deferred: bool,
) -> tuple[int, int, int, int, int, int, int, int, str]:
    deprioritized = 1 if notes.get("deprioritized") == "true" else 0
    attempt_count = int(runtime_state.get("attempt_count", 0) or 0)
    started = 0 if attempt_count == 0 else 1
    level = int(getattr(challenge, "level", 0) or 0)
    level_band, level_distance = _level_dispatch_priority(level, current_level)
    exp_priority = 0 if has_local_exp_support(getattr(challenge, "code", "")) and not deprioritized else 1
    difficulty_rank = _difficulty_priority(getattr(challenge, "difficulty", "unknown"))
    failure_count = int(runtime_state.get("failure_count", 0) or 0)
    return (
        exp_priority,
        level_band,
        level_distance,
        1 if deferred else 0,
        started,
        deprioritized,
        difficulty_rank,
        failure_count,
        getattr(challenge, "code", ""),
    )


def _challenge_is_locked(challenge: ChallengeSnapshot | Any, current_level: int | None) -> bool:
    if current_level is None:
        return False
    return int(getattr(challenge, "level", 0) or 0) > int(current_level)


def _level_dispatch_priority(level: int, current_level: int | None) -> tuple[int, int]:
    if current_level is None:
        return (0, level)
    if level == current_level:
        return (0, 0)
    if level < current_level:
        return (1, current_level - level)
    return (2, level - current_level)


def _difficulty_priority(raw: object) -> int:
    normalized = str(raw or "unknown").strip().lower()
    order = {
        "easy": 0,
        "medium": 1,
        "hard": 2,
        "insane": 3,
        "unknown": 9,
    }
    return order.get(normalized, 8)
