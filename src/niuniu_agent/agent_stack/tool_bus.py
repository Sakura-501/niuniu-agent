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
        result = await handler(**arguments)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    async def get_challenge_overview(self) -> str:
        snapshot = await self.context.challenge_store.refresh()
        return self.context.challenge_store.render_summary(snapshot)

    async def get_challenge_snapshot(self) -> dict[str, Any]:
        snapshot = await self.context.challenge_store.refresh()
        return self.context.challenge_store.export_json(snapshot)

    async def start_challenge(self, code: str) -> dict[str, Any]:
        payload = await self.context.challenge_store.contest_client.start_challenge(code)
        return {"code": code, "payload": payload}

    async def stop_challenge(self, code: str) -> dict[str, Any]:
        payload = await self.context.challenge_store.contest_client.stop_challenge(code)
        return {"code": code, "payload": payload}

    async def submit_flag(self, code: str, flag: str) -> dict[str, Any]:
        payload = await self.context.challenge_store.contest_client.submit_flag(code, flag)
        if isinstance(payload, dict) and payload.get("code") == 0:
            self.context.state_store.record_submitted_flag(code, flag)
        return {"code": code, "flag": flag, "payload": payload}

    async def view_hint(self, code: str) -> dict[str, Any]:
        payload = await self.context.challenge_store.contest_client.view_hint(code)
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
