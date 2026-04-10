from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI


@dataclass(slots=True)
class ToolEvent:
    name: str
    arguments: dict[str, Any]
    output: str


@dataclass(slots=True)
class AgentResult:
    output: str
    history: list[dict[str, Any]]
    tool_events: list[ToolEvent] = field(default_factory=list)


class AsyncPentestAgent:
    def __init__(
        self,
        client: AsyncOpenAI,
        model_name: str,
        system_prompt: str,
        tool_bus: Any,
        workdir: Path | str | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.tool_bus = tool_bus
        self.workdir = Path(workdir or Path.cwd()).resolve()
        self.temperature = temperature

    async def execute(self, instruction: str, history: list[dict[str, Any]] | None = None) -> AgentResult:
        transcript = list(history or [])
        transcript.append({"role": "user", "content": instruction})
        tool_events: list[ToolEvent] = []
        last_text = ""

        while True:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": self.system_prompt}, *transcript],
                tools=self.tool_bus.tool_schemas(),
                tool_choice="auto",
                temperature=self.temperature,
            )
            message = response.choices[0].message
            content = stringify_content(getattr(message, "content", ""))
            last_text = content or last_text
            tool_calls = list(getattr(message, "tool_calls", None) or [])
            transcript.append(assistant_message(content, tool_calls))
            if not tool_calls:
                return AgentResult(output=last_text, history=transcript, tool_events=tool_events)

            for tool_call in tool_calls:
                arguments = safe_load_json(tool_call.function.arguments)
                output = await self.tool_bus.dispatch(tool_call.function.name, arguments)
                tool_events.append(ToolEvent(tool_call.function.name, arguments, output))
                transcript.append({"role": "tool", "tool_call_id": tool_call.id, "content": output})


def assistant_message(content: str, tool_calls: list[Any]) -> dict[str, Any]:
    if not tool_calls:
        return {"role": "assistant", "content": content}
    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in tool_calls
        ],
    }


def stringify_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(stringify_content(item) for item in content)
    text = getattr(content, "text", None)
    if isinstance(text, str):
        return text
    return str(content)


def safe_load_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        return {"raw": raw}
