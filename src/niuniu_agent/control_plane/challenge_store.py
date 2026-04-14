from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot
from niuniu_agent.skills.tracks import infer_track


def compact_challenge_notes(
    notes: dict[str, str] | None,
    *,
    include_shared_findings: bool = False,
    value_limit: int = 600,
) -> dict[str, str]:
    compacted: dict[str, str] = {}
    for key, raw_value in sorted((notes or {}).items()):
        if key == "shared_findings" and not include_shared_findings:
            continue
        value = str(raw_value or "").strip()
        if not value:
            continue
        compacted[key] = value[:value_limit]
    return compacted


def extract_hint_context(
    notes: dict[str, str] | None,
    history: list[dict[str, object]] | None = None,
    memories: list[dict[str, object]] | None = None,
) -> dict[str, object] | None:
    notes = notes or {}
    history = history or []
    memories = memories or []
    hint_content = str(notes.get("hint_content") or "").strip()
    if not hint_content:
        for item in history:
            if item.get("event_type") == "hint_viewed":
                hint_content = extract_hint_text(item.get("payload"))
                if hint_content:
                    break
    if not hint_content:
        for item in memories:
            if str(item.get("memory_type") or "") not in {"persistent_hint", "hint_viewed"}:
                continue
            hint_content = extract_hint_text(item.get("content"))
            if hint_content:
                break
    hint_seen = notes.get("hint_viewed") == "true" or bool(hint_content)
    if not hint_seen:
        return None
    return {
        "hint_viewed": True,
        "hint_content": hint_content[:2000],
    }


def _iter_hint_candidates(payload: Any) -> list[str]:
    if payload is None:
        return []
    if isinstance(payload, str):
        value = payload.strip()
        if not value:
            return []
        try:
            decoded = json.loads(value)
        except Exception:
            return [value]
        return _iter_hint_candidates(decoded) or [value]
    if isinstance(payload, dict):
        ordered_keys = [
            "hint",
            "hint_content",
            "content",
            "text",
            "detail",
            "description",
            "message",
            "payload",
            "data",
        ]
        seen_keys: set[str] = set()
        candidates: list[str] = []
        for key in ordered_keys + [key for key in payload.keys() if str(key) not in seen_keys]:
            key_text = str(key)
            if key_text in seen_keys or key not in payload:
                continue
            seen_keys.add(key_text)
            candidates.extend(_iter_hint_candidates(payload.get(key)))
        return candidates
    if isinstance(payload, (list, tuple)):
        candidates: list[str] = []
        for item in payload:
            candidates.extend(_iter_hint_candidates(item))
        return candidates
    return [str(payload).strip()] if str(payload).strip() else []


def extract_hint_text(payload: Any) -> str:
    for candidate in _iter_hint_candidates(payload):
        normalized = candidate.strip()
        if normalized:
            return normalized[:2000]
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload.strip()[:2000]
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))[:2000]
    except TypeError:
        return str(payload).strip()[:2000]


def persist_hint_payload(
    state_store: Any,
    challenge_code: str,
    payload: Any,
    *,
    source: str = "system",
) -> dict[str, object]:
    hint_content = extract_hint_text(payload)
    state_store.add_history_event(challenge_code, "hint_viewed", hint_content or str(payload))
    state_store.set_challenge_note(challenge_code, "hint_viewed", "true")
    if hint_content:
        state_store.set_challenge_note(challenge_code, "hint_content", hint_content)
        state_store.add_challenge_memory(
            challenge_code,
            "persistent_hint",
            hint_content,
            source=source,
            persistent=True,
        )
    return {
        "hint_viewed": True,
        "hint_content": hint_content,
    }


class ChallengeStore:
    def __init__(self, contest_client: Any, state_store: Any, *, official_completion_grace_seconds: int = 30) -> None:
        self.contest_client = contest_client
        self.state_store = state_store
        self.official_completion_grace_seconds = official_completion_grace_seconds
        self._latest_snapshot: ContestSnapshot | None = None

    async def refresh(self) -> ContestSnapshot:
        payload = await self.contest_client.list_challenges()
        self._latest_snapshot = self.parse_payload(payload)
        self._reconcile_official_resets(self._latest_snapshot)
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
        current_level = current.current_level
        for challenge in sorted(
            current.challenges,
            key=lambda item: (
                _next_candidate_level_priority(item.level, current_level),
                _difficulty_priority(item.difficulty),
                item.code,
            ),
        ):
            if current_level is not None and challenge.level > current_level:
                continue
            if not self.is_effectively_completed(challenge):
                return challenge
        return None

    def is_effectively_completed(self, challenge: ChallengeSnapshot) -> bool:
        if challenge.completed:
            return True
        local_flags = self.state_store.list_submitted_flags(challenge.code)
        if challenge.flag_count > 0 and len(local_flags) >= challenge.flag_count:
            return True
        if self._uses_multi_flag_policy(challenge):
            return False
        if challenge.flag_count == 0 and local_flags:
            return True
        return False

    @staticmethod
    def _uses_multi_flag_policy(challenge: ChallengeSnapshot) -> bool:
        if getattr(challenge, "level", 0) >= 2:
            return True
        return infer_track(
            getattr(challenge, "description", ""),
            getattr(challenge, "code", None),
        ) in {"track3", "track4"}

    def render_summary(self, snapshot: ContestSnapshot | None = None) -> str:
        current = snapshot or self._latest_snapshot
        if current is None:
            return "No challenge snapshot available."

        lines = [
            f"current_level={current.current_level}",
            f"total_challenges={current.total_challenges}",
            f"solved_challenges={self._effective_solved_challenges(current)}",
        ]
        for challenge in current.challenges:
            local_flags = self.state_store.list_submitted_flags(challenge.code)
            lines.append(
                " - "
                f"{challenge.code} | {challenge.title} | "
                f"difficulty={challenge.difficulty} | level={challenge.level} | "
                f"instance={challenge.instance_status} | completed={self.is_effectively_completed(challenge)} | "
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
            "solved_challenges": self._effective_solved_challenges(current),
            "challenges": [
                {
                    **asdict(challenge),
                    "official_completed": challenge.completed,
                    "completed": self.is_effectively_completed(challenge),
                    "locally_submitted_flags": self.state_store.list_submitted_flags(challenge.code),
                    "runtime_state": self.state_store.get_challenge_runtime_state(challenge.code),
                    "notes": compact_challenge_notes(self.state_store.get_challenge_notes(challenge.code)),
                    "recent_history": self.state_store.list_history(challenge.code, limit=5),
                    "recent_memories": self.state_store.list_challenge_memories(challenge.code, limit=5),
                }
                for challenge in current.challenges
            ],
        }

    def build_autonomous_prompt(
        self,
        snapshot: ContestSnapshot,
        challenge: ChallengeSnapshot,
        *,
        stage: str | None = None,
        runtime_state: dict[str, object] | None = None,
        notes: dict[str, str] | None = None,
        track: str | None = None,
        selected_skills: list | None = None,
        available_skills: str | None = None,
        operator_resources: dict | None = None,
    ) -> str:
        recent_history = self.state_store.list_history(challenge.code, limit=5)
        notes = notes or compact_challenge_notes(self.state_store.get_challenge_notes(challenge.code))
        recent_memories = self.state_store.list_challenge_memories(challenge.code, limit=10)
        hint_context = extract_hint_context(notes, recent_history, recent_memories)
        if hint_context is not None and not notes.get("hint_content"):
            notes = {
                **notes,
                "hint_viewed": "true",
                "hint_content": str(hint_context.get("hint_content") or "")[:600],
            }
        from niuniu_agent.agent_stack.prompts import build_worker_runtime_instruction

        return build_worker_runtime_instruction(
            active=challenge,
            current_level=snapshot.current_level,
            runtime_state=runtime_state or self.state_store.get_challenge_runtime_state(challenge.code),
            notes=notes,
            recent_history=recent_history,
            recent_memories=recent_memories,
            selected_skills=selected_skills or [],
            stage=stage,
            track=track,
            operator_resources=operator_resources,
            hint_context=hint_context,
        )

    def _effective_solved_challenges(self, snapshot: ContestSnapshot) -> int:
        official = int(snapshot.solved_challenges or 0)
        local = sum(1 for challenge in snapshot.challenges if self.is_effectively_completed(challenge))
        return max(official, local)

    def _reconcile_official_resets(self, snapshot: ContestSnapshot, now: float | None = None) -> None:
        current = time.time() if now is None else now
        for challenge in snapshot.challenges:
            if challenge.completed:
                continue
            local_flags = self.state_store.list_submitted_flags(challenge.code)
            if not local_flags:
                continue
            if not hasattr(self.state_store, "latest_submitted_flag_at") or not hasattr(self.state_store, "clear_submitted_flags"):
                continue
            latest_local_flag_at = self.state_store.latest_submitted_flag_at(challenge.code)
            if latest_local_flag_at is None:
                continue
            if current - latest_local_flag_at < self.official_completion_grace_seconds:
                continue
            cleared = self.state_store.clear_submitted_flags(challenge.code)
            if cleared <= 0:
                continue
            self.state_store.add_history_event(
                challenge.code,
                "official_reset_detected",
                f"cleared {cleared} local submitted flag(s) because official snapshot shows unsolved state",
            )


def _next_candidate_level_priority(level: int, current_level: int | None) -> tuple[int, int]:
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
