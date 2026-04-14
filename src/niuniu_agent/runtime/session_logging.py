from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


def build_session_log_path(runtime_dir: Path | str, agent_id: str) -> Path:
    runtime_path = Path(runtime_dir)
    session_dir = runtime_path / "session_logs"
    safe_agent_id = re.sub(r"[^A-Za-z0-9._-]+", "_", agent_id).strip("_") or "anonymous"
    return session_dir / f"{safe_agent_id}_session.log"


class SessionTranscriptLogger:
    def __init__(
        self,
        path: Path,
        *,
        agent_id: str,
        agent_role: str | None = None,
        challenge_code: str | None = None,
    ) -> None:
        self.path = path
        self.agent_id = agent_id
        self.agent_role = agent_role
        self.challenge_code = challenge_code
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._started = False
        self._conversation_entries = 0

    @classmethod
    def for_agent(
        cls,
        runtime_dir: Path | str,
        *,
        agent_id: str,
        agent_role: str | None = None,
        challenge_code: str | None = None,
    ) -> "SessionTranscriptLogger":
        return cls(
            build_session_log_path(runtime_dir, agent_id),
            agent_id=agent_id,
            agent_role=agent_role,
            challenge_code=challenge_code,
        )

    def start(self, *, model_name: str, system_prompt: str) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._write_block(
                "SESSION START",
                self._stringify_content(
                    {
                        "agent_id": self.agent_id,
                        "agent_role": self.agent_role,
                        "challenge_code": self.challenge_code,
                        "model_name": model_name,
                    }
                ),
            )
            self._write_block("SYSTEM PROMPT", system_prompt)

    def replay_history(self, history: list[dict[str, Any]]) -> None:
        with self._lock:
            if self._conversation_entries > 0 or not history:
                return
            self._write_block(
                "HISTORY REPLAY",
                self._stringify_content({"message_count": len(history)}),
            )
            for message in history:
                self._write_message_locked(
                    role=str(message.get("role") or "unknown"),
                    content=message.get("content"),
                    metadata={key: value for key, value in message.items() if key not in {"role", "content"}},
                )

    def log_user(self, content: str) -> None:
        with self._lock:
            self._write_message_locked(role="user", content=content)

    def log_assistant(self, content: str, tool_calls: list[dict[str, Any]] | None = None) -> None:
        with self._lock:
            metadata: dict[str, Any] = {}
            if tool_calls:
                metadata["tool_calls"] = tool_calls
            self._write_message_locked(role="assistant", content=content, metadata=metadata)

    def log_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        with self._lock:
            self._conversation_entries += 1
            self._write_block(
                f"TOOL CALL {name}",
                self._stringify_content({"name": name, "arguments": arguments}),
            )

    def log_tool_result(self, name: str, output: str) -> None:
        with self._lock:
            self._conversation_entries += 1
            self._write_block(f"TOOL RESULT {name}", output)

    def log_compaction_start(self, *, source_message_count: int, kept_tail_count: int) -> None:
        with self._lock:
            self._write_block(
                "COMPACTION START",
                self._stringify_content(
                    {
                        "source_message_count": source_message_count,
                        "kept_tail_count": kept_tail_count,
                    }
                ),
            )

    def log_compaction_summary(self, summary: str) -> None:
        with self._lock:
            self._conversation_entries += 1
            self._write_block("COMPACTION SUMMARY", summary)

    def _write_message_locked(
        self,
        *,
        role: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._conversation_entries += 1
        body_parts = [self._stringify_content(content)]
        if metadata:
            body_parts.append(self._stringify_content(metadata))
        self._write_block(f"MESSAGE {role.upper()}", "\n".join(part for part in body_parts if part))

    def _write_block(self, title: str, content: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"===== {title} =====\n")
            handle.write(f"timestamp: {timestamp}\n")
            if title == "SESSION START":
                handle.write(f"agent_id: {self.agent_id}\n")
                if self.agent_role:
                    handle.write(f"agent_role: {self.agent_role}\n")
                if self.challenge_code:
                    handle.write(f"challenge_code: {self.challenge_code}\n")
            handle.write("\n")
            if content:
                handle.write(content.rstrip() + "\n")
            handle.write("\n")

    @staticmethod
    def _stringify_content(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True)
        except TypeError:
            return str(content)
