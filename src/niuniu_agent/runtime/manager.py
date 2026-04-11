from __future__ import annotations

import json
from dataclasses import dataclass, field

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.coordinator import CompetitionCoordinator
from niuniu_agent.runtime.findings_bus import ChallengeFindingsBus
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
        active_workers = [
            {"challenge_code": code, "task_running": coordinator.is_running(code)}
            for code in sorted(coordinator.worker_tasks.keys())
        ]
        pending = [challenge.code for challenge in snapshot.challenges if not challenge.completed]
        summary = f"active_workers={coordinator.active_count()} pending={len(pending)}"
        metadata = {
            "current_level": snapshot.current_level,
            "pending_challenges": pending,
            "active_workers": active_workers,
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
            payload=json.dumps(metadata, ensure_ascii=False),
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
            guidance = self._build_guidance(challenge)
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
    def _build_guidance(challenge: ChallengeSnapshot) -> str:
        track = infer_track(challenge.description)
        profile = TRACK_PROFILES.get(track)
        priorities = "\n".join(f"- {item}" for item in (profile.priorities if profile else ()))
        return (
            f"Manager guidance for {challenge.code} / {challenge.title}.\n"
            f"Track: {track}\n"
            f"Difficulty: {challenge.difficulty}\n"
            f"Entrypoints: {challenge.entrypoints}\n"
            "Priorities:\n"
            f"{priorities or '- follow the most deterministic next step'}"
        )
