from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from niuniu_agent.config import AgentSettings
from niuniu_agent.models import Challenge
from niuniu_agent.strategies.router import StrategyRouter
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox


class AgentController:
    def __init__(
        self,
        settings: AgentSettings,
        contest_client: Any,
        state_store: Any,
        event_logger: EventLogger,
        router: StrategyRouter,
        toolbox: LocalToolbox,
        solver: Any,
    ) -> None:
        self.settings = settings
        self.contest_client = contest_client
        self.state_store = state_store
        self.event_logger = event_logger
        self.router = router
        self.toolbox = toolbox
        self.solver = solver

    async def submit_candidate_flags(self, challenge_code: str, flags: list[str]) -> list[str]:
        submitted: list[str] = []
        seen: set[str] = set()

        for flag in flags:
            if flag in seen or self.state_store.has_submitted_flag(challenge_code, flag):
                continue
            seen.add(flag)

            result = await self.contest_client.submit_flag(challenge_code, flag)
            if isinstance(result, dict) and result.get("code") == 0:
                self.state_store.record_submitted_flag(challenge_code, flag)
                submitted.append(flag)
                self.event_logger.log(
                    "flag.submitted",
                    {"challenge_code": challenge_code, "flag": flag},
                )

        return submitted

    async def run_once(self, target_challenge_code: str | None = None) -> dict[str, Any]:
        payload = await self.contest_client.list_challenges()
        challenges = self.parse_challenges(payload)
        challenge = self.select_challenge(challenges, target_challenge_code)

        if challenge is None:
            self.event_logger.log("controller.idle", {"reason": "no-eligible-challenge"})
            return {"status": "idle"}

        strategy = self.router.route(challenge)
        self.event_logger.log(
            "challenge.selected",
            {"challenge_code": challenge.code, "track_id": strategy.track_id},
        )

        started = False
        try:
            start_result = await self.contest_client.start_challenge(challenge.code)
            challenge.entrypoints = self.extract_entrypoints(start_result)
            started = True
            self.event_logger.log(
                "challenge.started",
                {
                    "challenge_code": challenge.code,
                    "entrypoints": challenge.entrypoints,
                    "track_id": strategy.track_id,
                },
            )

            if self.solver is None:
                return {
                    "status": "planned",
                    "challenge": challenge.code,
                    "track_id": strategy.track_id,
                }

            result = await self.solver.run(
                strategy.system_prompt,
                self.build_user_prompt(challenge),
                self.toolbox,
            )

            evidence_text = result.final_text + "\n" + json.dumps(result.tool_events, ensure_ascii=True)
            candidate_flags = self.toolbox.extract_flags(evidence_text)
            submitted_flags = await self.submit_candidate_flags(challenge.code, candidate_flags)

            summary = {
                "status": "completed",
                "challenge": challenge.code,
                "track_id": strategy.track_id,
                "candidate_flags": candidate_flags,
                "submitted_flags": submitted_flags,
            }
            self.event_logger.log("challenge.completed", summary)
            return summary
        finally:
            if started and hasattr(self.contest_client, "stop_challenge"):
                try:
                    await self.contest_client.stop_challenge(challenge.code)
                except Exception as exc:  # pragma: no cover - defensive path for live runs
                    self.event_logger.log(
                        "challenge.stop_failed",
                        {"challenge_code": challenge.code, "error": str(exc)},
                    )

    def parse_challenges(self, payload: dict[str, Any] | Any) -> list[Challenge]:
        if not isinstance(payload, dict):
            return []

        data = payload.get("data", payload)
        raw_challenges = data.get("challenges", [])
        parsed: list[Challenge] = []
        for item in raw_challenges:
            parsed.append(
                Challenge(
                    code=item["code"],
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    difficulty=item.get("difficulty", "unknown"),
                    level=item.get("level", 1),
                    total_score=item.get("total_score", 0),
                    total_got_score=item.get("total_got_score", 0),
                    flag_count=item.get("flag_count", 0),
                    flag_got_count=item.get("flag_got_count", 0),
                    hint_viewed=item.get("hint_viewed", False),
                    instance_status=item.get("instance_status", "stopped"),
                    entrypoints=item.get("entrypoint") or [],
                )
            )
        return parsed

    def select_challenge(
        self,
        challenges: list[Challenge],
        target_challenge_code: str | None = None,
    ) -> Challenge | None:
        if target_challenge_code is not None:
            for challenge in challenges:
                if challenge.code == target_challenge_code:
                    return challenge
            return None

        for challenge in challenges:
            if not self.is_completed(challenge):
                return challenge
        return None

    @staticmethod
    def is_completed(challenge: Challenge) -> bool:
        if challenge.flag_count > 0:
            return challenge.flag_got_count >= challenge.flag_count
        if challenge.total_score > 0:
            return challenge.total_got_score >= challenge.total_score
        return False

    @staticmethod
    def extract_entrypoints(payload: Any) -> list[str]:
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return [str(item) for item in data]
            if isinstance(data, dict):
                return []
        if isinstance(payload, list):
            return [str(item) for item in payload]
        return []

    @staticmethod
    def build_user_prompt(challenge: Challenge) -> str:
        prompt = {
            "challenge": asdict(challenge),
            "instructions": [
                "Enumerate the exposed surface first.",
                "Use the available tools to gather concrete evidence before claiming a flag.",
                "Return any discovered flag values explicitly.",
            ],
        }
        return json.dumps(prompt, ensure_ascii=True)
