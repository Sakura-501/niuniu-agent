from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot


class ChallengeStore:
    def __init__(self, contest_client: Any, state_store: Any) -> None:
        self.contest_client = contest_client
        self.state_store = state_store
        self._latest_snapshot: ContestSnapshot | None = None

    async def refresh(self) -> ContestSnapshot:
        payload = await self.contest_client.list_challenges()
        self._latest_snapshot = self.parse_payload(payload)
        return self._latest_snapshot

    @property
    def latest(self) -> ContestSnapshot | None:
        return self._latest_snapshot

    def parse_payload(self, payload: dict[str, Any] | Any) -> ContestSnapshot:
        if not isinstance(payload, dict):
            return ContestSnapshot(current_level=None, total_challenges=0, solved_challenges=None, challenges=[])

        data = payload.get("data", payload)
        raw_challenges = data.get("challenges", [])
        challenges = [
            ChallengeSnapshot(
                code=item["code"],
                title=item.get("title", ""),
                description=item.get("description", ""),
                difficulty=item.get("difficulty", "unknown"),
                level=item.get("level", 0),
                total_score=item.get("total_score", 0),
                total_got_score=item.get("total_got_score", 0),
                flag_count=item.get("flag_count", 0),
                flag_got_count=item.get("flag_got_count", 0),
                hint_viewed=item.get("hint_viewed", False),
                instance_status=item.get("instance_status", "stopped"),
                entrypoints=item.get("entrypoint") or [],
            )
            for item in raw_challenges
        ]
        return ContestSnapshot(
            current_level=data.get("current_level"),
            total_challenges=data.get("total_challenges", len(challenges)),
            solved_challenges=data.get("solved_challenges"),
            challenges=challenges,
        )

    def next_candidate(self, snapshot: ContestSnapshot | None = None) -> ChallengeSnapshot | None:
        current = snapshot or self._latest_snapshot
        if current is None:
            return None
        for challenge in sorted(current.challenges, key=lambda item: (item.level, item.completed, item.code)):
            if not challenge.completed:
                return challenge
        return None

    def render_summary(self, snapshot: ContestSnapshot | None = None) -> str:
        current = snapshot or self._latest_snapshot
        if current is None:
            return "No challenge snapshot available."

        lines = [
            f"current_level={current.current_level}",
            f"total_challenges={current.total_challenges}",
            f"solved_challenges={current.solved_challenges}",
        ]
        for challenge in current.challenges:
            local_flags = self.state_store.list_submitted_flags(challenge.code)
            lines.append(
                " - "
                f"{challenge.code} | {challenge.title} | "
                f"difficulty={challenge.difficulty} | level={challenge.level} | "
                f"instance={challenge.instance_status} | completed={challenge.completed} | "
                f"hint_viewed={challenge.hint_viewed} | local_flags={len(local_flags)}"
            )
        return "\n".join(lines)

    def export_json(self, snapshot: ContestSnapshot | None = None) -> dict[str, Any]:
        current = snapshot or self._latest_snapshot
        if current is None:
            return {"current_level": None, "total_challenges": 0, "solved_challenges": None, "challenges": []}
        return {
            "current_level": current.current_level,
            "total_challenges": current.total_challenges,
            "solved_challenges": current.solved_challenges,
            "challenges": [
                {
                    **asdict(challenge),
                    "completed": challenge.completed,
                    "locally_submitted_flags": self.state_store.list_submitted_flags(challenge.code),
                    "runtime_state": self.state_store.get_challenge_runtime_state(challenge.code),
                    "notes": self.state_store.get_challenge_notes(challenge.code),
                }
                for challenge in current.challenges
            ],
        }

    def build_autonomous_prompt(self, snapshot: ContestSnapshot, challenge: ChallengeSnapshot) -> str:
        return json.dumps(
            {
                "mode": "competition",
                "contest_snapshot": self.export_json(snapshot),
                "active_challenge": asdict(challenge),
                "instructions": [
                    "Work on the selected challenge autonomously.",
                    "Use available MCP and local tools.",
                    "Submit any discovered flags immediately.",
                    "Do not stop because of uncertainty; gather evidence and continue.",
                ],
            },
            ensure_ascii=False,
        )
