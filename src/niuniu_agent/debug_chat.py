from __future__ import annotations

import json
from typing import Any

import typer

from niuniu_agent.controller import AgentController
from niuniu_agent.llm import AgentRunResult


class DebugToolbox:
    def __init__(self, controller: AgentController) -> None:
        self.controller = controller

    def describe_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_challenges",
                    "description": "Refresh and return the current challenge overview, including completion state.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "start_challenge",
                    "description": "Start a challenge instance and return entrypoints.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "stop_challenge",
                    "description": "Stop a challenge instance.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "submit_flag",
                    "description": "Submit a flag for a challenge.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "flag": {"type": "string"},
                        },
                        "required": ["code", "flag"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "view_hint",
                    "description": "View a hint for a challenge.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                        },
                        "required": ["code"],
                    },
                },
            },
            *self.controller.toolbox.describe_tools(),
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "list_challenges":
            return await self.list_challenges()
        if tool_name == "start_challenge":
            return await self.start_challenge(arguments["code"])
        if tool_name == "stop_challenge":
            return await self.stop_challenge(arguments["code"])
        if tool_name == "submit_flag":
            return await self.submit_flag(arguments["code"], arguments["flag"])
        if tool_name == "view_hint":
            return await self.view_hint(arguments["code"])

        return await self.controller.toolbox.execute(tool_name, arguments)

    async def list_challenges(self) -> dict[str, Any]:
        payload = await self.controller.contest_client.list_challenges()
        challenges = self.controller.parse_challenges(payload)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}

        return {
            "current_level": data.get("current_level"),
            "total_challenges": data.get("total_challenges", len(challenges)),
            "solved_challenges": data.get("solved_challenges"),
            "challenges": [self._serialize_challenge(challenge) for challenge in challenges],
        }

    async def start_challenge(self, code: str) -> dict[str, Any]:
        payload = await self.controller.contest_client.start_challenge(code)
        entrypoints = self.controller.extract_entrypoints(payload)
        return {"code": code, "entrypoints": entrypoints, "raw": payload}

    async def stop_challenge(self, code: str) -> dict[str, Any]:
        payload = await self.controller.contest_client.stop_challenge(code)
        return {"code": code, "raw": payload}

    async def submit_flag(self, code: str, flag: str) -> dict[str, Any]:
        submitted = await self.controller.submit_candidate_flags(code, [flag])
        return {"code": code, "submitted_flags": submitted}

    async def view_hint(self, code: str) -> dict[str, Any]:
        payload = await self.controller.contest_client.view_hint(code)
        return {"code": code, "raw": payload}

    def _serialize_challenge(self, challenge) -> dict[str, Any]:
        return {
            "code": challenge.code,
            "title": challenge.title,
            "difficulty": challenge.difficulty,
            "level": challenge.level,
            "description": challenge.description,
            "instance_status": challenge.instance_status,
            "entrypoints": challenge.entrypoints,
            "completed": self.controller.is_completed(challenge),
            "hint_viewed": challenge.hint_viewed,
            "flag_count": challenge.flag_count,
            "flag_got_count": challenge.flag_got_count,
            "locally_submitted_flags": self.controller.state_store.list_submitted_flags(challenge.code),
        }


def build_debug_system_prompt() -> str:
    return (
        "You are the debug-mode operator assistant for a pentest contest agent. "
        "Always reason from the live challenge state. "
        "Use contest tools to refresh challenge status, start instances, stop instances, "
        "view hints, and submit flags when needed. "
        "Use local tools for HTTP, shell, and Python-driven debugging. "
        "When replying, clearly state which challenge you are working on, which ones are completed, "
        "and what action you took."
    )


def build_debug_user_message(challenge_snapshot: dict[str, Any], user_input: str) -> str:
    return json.dumps(
        {
            "challenge_snapshot": challenge_snapshot,
            "user_request": user_input,
        },
        ensure_ascii=True,
    )


def format_challenge_snapshot(snapshot: dict[str, Any]) -> str:
    lines = [
        f"current_level={snapshot.get('current_level')}",
        f"total_challenges={snapshot.get('total_challenges')}",
    ]
    for challenge in snapshot.get("challenges", []):
        lines.append(
            " - "
            f"{challenge['code']} | {challenge['title']} | "
            f"difficulty={challenge['difficulty']} | "
            f"status={challenge['instance_status']} | "
            f"completed={challenge['completed']} | "
            f"local_flags={len(challenge['locally_submitted_flags'])}"
        )
    return "\n".join(lines)


def _short_json(value: Any, limit: int = 240) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def render_debug_turn(result: AgentRunResult) -> str:
    lines: list[str] = []

    for event in result.tool_events:
        lines.append(f"[tool] {event['tool']}")
        lines.append(f"  args: {_short_json(event['arguments'])}")
        lines.append(f"  result: {_short_json(event['result'])}")

    if result.iteration_limit_reached:
        lines.append("本轮模型已达到工具调用上限，未产出最终自然语言答复。")
        lines.append("可以继续追问，或调大 NIUNIU_AGENT_LLM_MAX_ITERATIONS。")
    elif result.final_text:
        lines.append(result.final_text)
    else:
        lines.append("[assistant produced no text]")

    return "\n".join(lines)


async def run_debug_chat(controller: AgentController) -> None:
    toolbox = DebugToolbox(controller=controller)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_debug_system_prompt()},
    ]

    typer.echo("已进入交互式调试模式。输入 exit 或 quit 退出。")
    snapshot = await toolbox.list_challenges()
    typer.echo(format_challenge_snapshot(snapshot))

    while True:
        user_input = typer.prompt("debug")
        if user_input.strip().lower() in {"exit", "quit", "/exit", "/quit"}:
            break

        snapshot = await toolbox.list_challenges()
        controller.event_logger.log(
            "debug.user_turn",
            {"message": user_input},
        )
        messages.append(
            {
                "role": "user",
                "content": build_debug_user_message(snapshot, user_input),
            }
        )

        result: AgentRunResult = await controller.solver.run_messages(messages, toolbox)
        messages = result.messages
        rendered = render_debug_turn(result)
        controller.event_logger.log(
            "debug.assistant_turn",
            {"message": rendered},
        )
        typer.echo(rendered)
