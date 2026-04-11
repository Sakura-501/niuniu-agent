from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from niuniu_agent.runtime.context import RuntimeContext


@dataclass(slots=True)
class RuntimeTool:
    name: str
    description: str
    input_schema: dict[str, Any]

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class ToolBus:
    def __init__(self, context: RuntimeContext) -> None:
        self.context = context
        self._handlers = {
            "get_challenge_overview": self.get_challenge_overview,
            "get_challenge_snapshot": self.get_challenge_snapshot,
            "check_tool_inventory": self.check_tool_inventory,
            "get_challenge_history": self.get_challenge_history,
            "get_challenge_notes": self.get_challenge_notes,
            "set_challenge_note": self.set_challenge_note,
            "start_challenge": self.start_challenge,
            "stop_challenge": self.stop_challenge,
            "submit_flag": self.submit_flag,
            "view_hint": self.view_hint,
            "http_request": self.http_request,
            "run_shell_command": self.run_shell_command,
            "run_python_snippet": self.run_python_snippet,
            "get_local_runtime_state": self.get_local_runtime_state,
        }

    @property
    def tools(self) -> list[RuntimeTool]:
        return [
            RuntimeTool("get_challenge_overview", "Refresh and summarize contest challenges.", {"type": "object", "properties": {}}),
            RuntimeTool("get_challenge_snapshot", "Return the latest contest snapshot as JSON.", {"type": "object", "properties": {}}),
            RuntimeTool("check_tool_inventory", "Return local tool availability and install hints.", {"type": "object", "properties": {}}),
            RuntimeTool(
                "get_challenge_history",
                "Return recent history events for a challenge.",
                {"type": "object", "properties": {"code": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["code"]},
            ),
            RuntimeTool(
                "get_challenge_notes",
                "Return stored notes for a challenge.",
                {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
            ),
            RuntimeTool(
                "set_challenge_note",
                "Store a short note for a challenge, such as foothold or conclusion.",
                {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "note_key": {"type": "string"},
                        "note_value": {"type": "string"},
                    },
                    "required": ["code", "note_key", "note_value"],
                },
            ),
            RuntimeTool(
                "start_challenge",
                "Start a challenge instance through the official contest control plane.",
                {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
            ),
            RuntimeTool(
                "stop_challenge",
                "Stop a challenge instance through the official contest control plane.",
                {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
            ),
            RuntimeTool(
                "submit_flag",
                "Submit a candidate flag for a challenge.",
                {
                    "type": "object",
                    "properties": {"code": {"type": "string"}, "flag": {"type": "string"}},
                    "required": ["code", "flag"],
                },
            ),
            RuntimeTool(
                "view_hint",
                "View a hint for a challenge.",
                {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
            ),
            RuntimeTool(
                "http_request",
                "Send an HTTP request to a target endpoint.",
                {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "url": {"type": "string"},
                        "body": {"type": "string"},
                        "timeout_seconds": {"type": "integer"},
                    },
                    "required": ["method", "url"],
                },
            ),
            RuntimeTool(
                "run_shell_command",
                "Run a shell command locally.",
                {
                    "type": "object",
                    "properties": {"command": {"type": "string"}, "timeout_seconds": {"type": "integer"}},
                    "required": ["command"],
                },
            ),
            RuntimeTool(
                "run_python_snippet",
                "Run a Python snippet locally.",
                {
                    "type": "object",
                    "properties": {"code": {"type": "string"}, "timeout_seconds": {"type": "integer"}},
                    "required": ["code"],
                },
            ),
            RuntimeTool("get_local_runtime_state", "Return local notes and state summary.", {"type": "object", "properties": {}}),
        ]

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [tool.openai_schema() for tool in self.tools]

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        handler = self._handlers.get(name)
        if handler is None:
            return f"Unknown tool: {name}"
        try:
            result = await handler(**arguments)
        except TypeError as exc:
            return f"Error calling tool '{name}': {exc}"
        except Exception as exc:  # noqa: BLE001
            return f"Error calling tool '{name}': {exc}"
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    async def get_challenge_overview(self) -> str:
        snapshot = await self.context.challenge_store.refresh()
        return self.context.challenge_store.render_summary(snapshot)

    async def get_challenge_snapshot(self) -> dict[str, Any]:
        snapshot = await self.context.challenge_store.refresh()
        return self.context.challenge_store.export_json(snapshot)

    async def check_tool_inventory(self) -> dict[str, Any]:
        return await self.context.local_toolbox.check_tool_inventory()

    async def get_challenge_history(self, code: str, limit: int = 10) -> dict[str, Any]:
        return {"code": code, "history": self.context.state_store.list_history(code, limit)}

    async def get_challenge_notes(self, code: str) -> dict[str, Any]:
        return {"code": code, "notes": self.context.state_store.get_challenge_notes(code)}

    async def set_challenge_note(self, code: str, note_key: str, note_value: str) -> dict[str, Any]:
        self.context.state_store.set_challenge_note(code, note_key, note_value)
        return {"code": code, "note_key": note_key, "note_value": note_value}

    async def start_challenge(self, code: str) -> dict[str, Any]:
        try:
            snapshot = await self.context.challenge_store.refresh()
            running = [challenge.code for challenge in snapshot.challenges if challenge.instance_status == "running" and challenge.code != code]
            stopped: list[str] = []
            if len(running) >= 3:
                for running_code in running:
                    await self.context.contest_gateway.stop_challenge(running_code)
                    stopped.append(running_code)
            payload = await self.context.contest_gateway.start_challenge(code)
            return {"code": code, "payload": payload, "stopped": stopped, "running_count_before": len(running)}
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if "最多同时运行3个实例" not in message:
                raise

            snapshot = await self.context.challenge_store.refresh()
            stopped: list[str] = []
            for challenge in snapshot.challenges:
                if challenge.code == code:
                    continue
                if challenge.instance_status == "running":
                    try:
                        await self.context.contest_gateway.stop_challenge(challenge.code)
                        stopped.append(challenge.code)
                    except Exception as stop_exc:  # noqa: BLE001
                        return {
                            "code": code,
                            "stopped": stopped,
                            "error": f"instance limit reached, and stopping {challenge.code} failed: {stop_exc}",
                        }

            retry_payload = await self.context.contest_gateway.start_challenge(code)
            return {"code": code, "payload": retry_payload, "stopped": stopped}

    async def stop_challenge(self, code: str) -> dict[str, Any]:
        payload = await self.context.contest_gateway.stop_challenge(code)
        return {"code": code, "payload": payload}

    async def submit_flag(self, code: str, flag: str) -> dict[str, Any]:
        payload = await self.context.contest_gateway.submit_flag(code, flag)
        if self._is_successful_flag_submission(payload):
            self.context.state_store.record_submitted_flag(code, flag)
            self.context.state_store.add_history_event(code, "flag_submitted", json.dumps({"flag": flag, "payload": payload}, ensure_ascii=False))
            self.context.state_store.set_challenge_note(code, "last_flag", flag)
        snapshot = await self.context.challenge_store.refresh()
        challenge = next((item for item in snapshot.challenges if item.code == code), None)
        stopped_instance = False
        if challenge is not None and challenge.completed and challenge.instance_status == "running":
            await self.context.contest_gateway.stop_challenge(code)
            stopped_instance = True
        return {
            "code": code,
            "flag": flag,
            "payload": payload,
            "completed": challenge.completed if challenge is not None else False,
            "stopped_instance": stopped_instance,
        }

    @staticmethod
    def _is_successful_flag_submission(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        if payload.get("code") == 0:
            return True
        if payload.get("correct") is True:
            return True
        message = str(payload.get("message", "")).lower()
        return any(
            marker in message
            for marker in (
                "答案正确",
                "correct",
                "already solved",
                "已完成",
                "已全部答对",
                "无需重复提交",
            )
        )

    async def view_hint(self, code: str) -> dict[str, Any]:
        payload = await self.context.contest_gateway.view_hint(code)
        return {"code": code, "payload": payload}

    async def http_request(self, method: str, url: str, body: str | None = None, timeout_seconds: int = 20) -> dict[str, Any]:
        return await self.context.local_toolbox.http_request(method=method, url=url, body=body, timeout_seconds=timeout_seconds)

    async def run_shell_command(self, command: str, timeout_seconds: int = 30) -> dict[str, Any]:
        return await self.context.local_toolbox.run_shell_command(command=command, timeout_seconds=timeout_seconds)

    async def run_python_snippet(self, code: str, timeout_seconds: int = 30) -> dict[str, Any]:
        return await self.context.local_toolbox.run_python_snippet(code=code, timeout_seconds=timeout_seconds)

    async def get_local_runtime_state(self) -> dict[str, Any]:
        return {
            "notes": self.context.notes,
            "snapshot": self.context.challenge_store.export_json(self.context.challenge_store.latest),
        }
