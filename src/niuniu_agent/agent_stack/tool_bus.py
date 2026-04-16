from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from niuniu_agent.control_plane.challenge_store import compact_challenge_notes, persist_hint_payload
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.skills.tracks import infer_track


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
    AUTO_FLAG_SUBMISSION_TOOLS = frozenset({"http_request", "run_shell_command", "run_python_snippet", "webshell_exec"})

    def __init__(self, context: RuntimeContext) -> None:
        self.context = context
        self._handlers = {
            "get_challenge_overview": self.get_challenge_overview,
            "get_challenge_snapshot": self.get_challenge_snapshot,
            "check_tool_inventory": self.check_tool_inventory,
            "load_skill": self.load_skill,
            "get_challenge_history": self.get_challenge_history,
            "get_challenge_notes": self.get_challenge_notes,
            "get_challenge_memories": self.get_challenge_memories,
            "set_challenge_note": self.set_challenge_note,
            "start_challenge": self.start_challenge,
            "stop_challenge": self.stop_challenge,
            "submit_flag": self.submit_flag,
            "view_hint": self.view_hint,
            "http_request": self.http_request,
            "run_shell_command": self.run_shell_command,
            "run_python_snippet": self.run_python_snippet,
            "webshell_exec": self.webshell_exec,
            "get_local_runtime_state": self.get_local_runtime_state,
        }
        self._tools = [
            RuntimeTool("get_challenge_overview", "Refresh and summarize contest challenges.", {"type": "object", "properties": {}}),
            RuntimeTool("get_challenge_snapshot", "Return the latest contest snapshot as JSON.", {"type": "object", "properties": {}}),
            RuntimeTool("check_tool_inventory", "Return local tool availability and install hints.", {"type": "object", "properties": {}}),
            RuntimeTool(
                "load_skill",
                "Load the full body of a named skill into the current context.",
                {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            ),
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
                "get_challenge_memories",
                "Return persisted memory items for a challenge.",
                {"type": "object", "properties": {"code": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["code"]},
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
                            "headers": {"type": "object", "additionalProperties": {"type": "string"}},
                            "params": {"type": "object", "additionalProperties": {"type": "string"}},
                            "cookies": {"type": "object", "additionalProperties": {"type": "string"}},
                            "form": {"type": "object", "additionalProperties": {"type": "string"}},
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "filename": {"type": "string"},
                                        "content": {"type": "string"},
                                        "content_type": {"type": "string"},
                                    },
                                    "required": ["name", "filename", "content"],
                                },
                            },
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
            RuntimeTool(
                "webshell_exec",
                "Execute a command through an existing webshell endpoint using a command parameter.",
                {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "command": {"type": "string"},
                        "method": {"type": "string"},
                        "param_name": {"type": "string"},
                        "headers": {"type": "object", "additionalProperties": {"type": "string"}},
                        "params": {"type": "object", "additionalProperties": {"type": "string"}},
                        "timeout_seconds": {"type": "integer"},
                        "expect_marker": {"type": "string"},
                    },
                    "required": ["url", "command"],
                },
            ),
            RuntimeTool("get_local_runtime_state", "Return local notes and state summary.", {"type": "object", "properties": {}}),
        ]
        self._tool_schemas_cache = [tool.openai_schema() for tool in self._tools]

    @property
    def tools(self) -> list[RuntimeTool]:
        return self._tools

    def tool_schemas(self) -> list[dict[str, Any]]:
        return self._tool_schemas_cache

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        handler = self._handlers.get(name)
        if handler is None:
            return f"Unknown tool: {name}"
        self._record_agent_event("tool_start", {"name": name, "arguments": arguments})
        try:
            result = await handler(**arguments)
        except TypeError as exc:
            output = f"Error calling tool '{name}': {exc}"
            self._record_agent_event("tool_error", {"name": name, "arguments": arguments, "error": str(exc)})
            return output
        except Exception as exc:  # noqa: BLE001
            output = f"Error calling tool '{name}': {exc}"
            self._record_agent_event("tool_error", {"name": name, "arguments": arguments, "error": str(exc)})
            return output
        auto_submitted_flags = await self._auto_submit_flags_if_needed(name, result)
        if auto_submitted_flags and isinstance(result, dict):
            result = {**result, "auto_submitted_flags": auto_submitted_flags}
        if isinstance(result, str):
            self._record_agent_event("tool_done", {"name": name, "arguments": arguments, "output_preview": result[:300]})
            return result
        output = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self._record_agent_event("tool_done", {"name": name, "arguments": arguments, "output_preview": output[:300]})
        return output

    async def _auto_submit_flags_if_needed(self, tool_name: str, result: Any) -> list[dict[str, Any]]:
        if tool_name not in self.AUTO_FLAG_SUBMISSION_TOOLS:
            return []
        challenge_code = self.context.challenge_code
        if not challenge_code:
            return []
        flags = self._extract_flags_from_value(result)
        if not flags:
            return []
        submissions: list[dict[str, Any]] = []
        for flag in flags:
            try:
                submission = await self.submit_flag(challenge_code, flag)
                submissions.append(submission)
                self._record_agent_event(
                    "auto_flag_submit",
                    {"source_tool": tool_name, "challenge_code": challenge_code, "flag": flag},
                )
            except Exception as exc:  # noqa: BLE001
                submissions.append({"code": challenge_code, "flag": flag, "error": str(exc)})
                self._record_agent_event(
                    "auto_flag_submit_error",
                    {"source_tool": tool_name, "challenge_code": challenge_code, "flag": flag, "error": str(exc)},
                )
        return submissions

    def _extract_flags_from_value(self, value: Any) -> list[str]:
        candidates: list[str] = []

        def _walk(node: Any) -> None:
            if isinstance(node, str):
                candidates.extend(self.context.local_toolbox.extract_flags(node))
                return
            if isinstance(node, dict):
                for nested in node.values():
                    _walk(nested)
                return
            if isinstance(node, (list, tuple, set)):
                for nested in node:
                    _walk(nested)

        _walk(value)
        deduped: list[str] = []
        seen: set[str] = set()
        for flag in candidates:
            if flag in seen:
                continue
            seen.add(flag)
            deduped.append(flag)
        return deduped

    async def auto_submit_text_output(self, text: str) -> list[dict[str, Any]]:
        challenge_code = self.context.challenge_code
        if not challenge_code:
            return []
        flags = self._extract_flags_from_value(text)
        if not flags:
            return []
        submissions: list[dict[str, Any]] = []
        for flag in flags:
            try:
                submission = await self.submit_flag(challenge_code, flag)
                submissions.append(submission)
                self._record_agent_event(
                    "auto_flag_submit",
                    {"source_tool": "assistant_text", "challenge_code": challenge_code, "flag": flag},
                )
            except Exception as exc:  # noqa: BLE001
                submissions.append({"code": challenge_code, "flag": flag, "error": str(exc)})
                self._record_agent_event(
                    "auto_flag_submit_error",
                    {"source_tool": "assistant_text", "challenge_code": challenge_code, "flag": flag, "error": str(exc)},
                )
        return submissions

    async def get_challenge_overview(self) -> str:
        snapshot = await self.context.challenge_store.refresh()
        return self.context.challenge_store.render_summary(snapshot)

    async def get_challenge_snapshot(self) -> dict[str, Any]:
        snapshot = await self.context.challenge_store.refresh()
        return self.context.challenge_store.export_json(snapshot)

    async def check_tool_inventory(self) -> dict[str, Any]:
        return await self.context.local_toolbox.check_tool_inventory()

    async def load_skill(self, name: str) -> str:
        if self.context.skill_registry is None:
            return "Error: skill registry unavailable"
        return self.context.skill_registry.load_full_text(name)

    async def get_challenge_history(self, code: str, limit: int = 10) -> dict[str, Any]:
        return {"code": code, "history": self.context.state_store.list_history(code, limit)}

    async def get_challenge_notes(self, code: str) -> dict[str, Any]:
        return {"code": code, "notes": self.context.state_store.get_challenge_notes(code)}

    async def get_challenge_memories(self, code: str, limit: int = 10) -> dict[str, Any]:
        return {"code": code, "memories": self.context.state_store.list_challenge_memories(code, limit)}

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
        try:
            payload = await self.context.contest_gateway.stop_challenge(code)
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if "赛题实例未运行" not in message and "not running" not in message.lower():
                raise
            return {"code": code, "already_stopped": True}
        return {"code": code, "payload": payload}

    async def submit_flag(self, code: str, flag: str) -> dict[str, Any]:
        try:
            payload = await self.context.contest_gateway.submit_flag(code, flag)
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if "赛题实例未运行" not in message:
                raise
            await self.start_challenge(code)
            payload = await self.context.contest_gateway.submit_flag(code, flag)
        if self._is_successful_flag_submission(payload):
            self.context.state_store.record_submitted_flag(code, flag)
            self.context.state_store.add_history_event(code, "flag_submitted", json.dumps({"flag": flag, "payload": payload}, ensure_ascii=False, sort_keys=True))
            self.context.state_store.set_challenge_note(code, "last_flag", flag)
            self.context.state_store.add_challenge_memory(code, "flag_submitted", flag, source="submit_flag")
        snapshot = await self.context.challenge_store.refresh()
        challenge = next((item for item in snapshot.challenges if item.code == code), None)
        self._persist_flag_path_memory(challenge, code, flag, payload)
        effective_completed = self.context.challenge_store.is_effectively_completed(challenge) if challenge is not None else False
        stopped_instance = False
        if challenge is not None and effective_completed and challenge.instance_status == "running":
            await self.context.contest_gateway.stop_challenge(code)
            stopped_instance = True
        return {
            "code": code,
            "flag": flag,
            "payload": payload,
            "completed": effective_completed,
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

    def _persist_flag_path_memory(self, challenge: Any, code: str, flag: str, payload: Any) -> None:
        if challenge is None or not self._should_persist_critical_memory(challenge):
            return
        progress = {}
        if isinstance(payload, dict):
            nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
            progress = {
                "flag_count": nested.get("flag_count"),
                "flag_got_count": nested.get("flag_got_count"),
                "message": nested.get("message"),
            }
        summary_parts = [f"flag={flag}"]
        if progress.get("flag_count") is not None or progress.get("flag_got_count") is not None:
            summary_parts.append(
                f"progress={progress.get('flag_got_count')}/{progress.get('flag_count')}"
            )
        self.context.state_store.add_challenge_memory(
            code,
            "persistent_flag_record",
            "\n".join(summary_parts),
            source="submit_flag",
            persistent=True,
        )

    @staticmethod
    def _should_persist_critical_memory(challenge: Any) -> bool:
        if int(getattr(challenge, "level", 0) or 0) >= 2:
            return True
        return infer_track(
            str(getattr(challenge, "description", "")),
            str(getattr(challenge, "code", "")) or None,
        ) in {"track3", "track4"}

    async def view_hint(self, code: str) -> dict[str, Any]:
        payload = await self.context.contest_gateway.view_hint(code)
        hint_context = persist_hint_payload(
            self.context.state_store,
            code,
            payload,
            source=self.context.agent_id or "view_hint",
        )
        return {"code": code, "payload": payload, "hint_context": hint_context}

    async def http_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        files: list[dict[str, str]] | None = None,
        body: str | None = None,
        timeout_seconds: int = 20,
    ) -> dict[str, Any]:
        return await self.context.local_toolbox.http_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            cookies=cookies,
            form=form,
            files=files,
            body=body,
            timeout_seconds=timeout_seconds,
        )

    async def run_shell_command(self, command: str, timeout_seconds: int = 30) -> dict[str, Any]:
        return await self.context.local_toolbox.run_shell_command(command=command, timeout_seconds=timeout_seconds)

    async def run_python_snippet(self, code: str, timeout_seconds: int = 30) -> dict[str, Any]:
        return await self.context.local_toolbox.run_python_snippet(code=code, timeout_seconds=timeout_seconds)

    async def webshell_exec(
        self,
        url: str,
        command: str,
        method: str = "GET",
        param_name: str = "cmd",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout_seconds: int = 20,
        expect_marker: str | None = None,
    ) -> dict[str, Any]:
        return await self.context.local_toolbox.webshell_exec(
            url=url,
            command=command,
            method=method,
            param_name=param_name,
            headers=headers,
            params=params,
            timeout_seconds=timeout_seconds,
            expect_marker=expect_marker,
        )

    async def get_local_runtime_state(self) -> dict[str, Any]:
        return {
            "notes": self.context.notes,
            "snapshot": self.context.challenge_store.export_json(self.context.challenge_store.latest),
            "operator_resources": {
                "callback_server": self.context.settings.callback_resource,
            }
            if self.context.settings.callback_resource
            else {},
        }

    def _record_agent_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.context.agent_id:
            return
        challenge_code = self.context.challenge_code or payload.get("code")
        self.context.state_store.append_agent_event(
            agent_id=self.context.agent_id,
            challenge_code=str(challenge_code) if challenge_code else None,
            event_type=event_type,
            payload=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        )
