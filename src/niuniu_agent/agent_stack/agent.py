from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

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


@dataclass(slots=True)
class ToolCallData:
    id: str
    name: str
    arguments: str


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
        return await self._execute_loop(instruction, history, on_text_delta=None)

    async def execute_stream(
        self,
        instruction: str,
        history: list[dict[str, Any]] | None = None,
        on_text_delta: Callable[[str], Awaitable[None]] | None = None,
        on_tool_start: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
        on_tool_end: Callable[[str, dict[str, Any], str], Awaitable[None]] | None = None,
    ) -> AgentResult:
        return await self._execute_loop(
            instruction,
            history,
            on_text_delta=on_text_delta,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        )

    async def _execute_loop(
        self,
        instruction: str,
        history: list[dict[str, Any]] | None,
        on_text_delta: Callable[[str], Awaitable[None]] | None,
        on_tool_start: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
        on_tool_end: Callable[[str, dict[str, Any], str], Awaitable[None]] | None = None,
    ) -> AgentResult:
        transcript = list(history or [])
        transcript.append({"role": "user", "content": instruction})
        tool_events: list[ToolEvent] = []
        last_text = ""

        while True:
            content, tool_calls = await self._complete_once(transcript, on_text_delta=on_text_delta)
            last_text = content or last_text
            transcript.append(assistant_message(content, tool_calls))
            if not tool_calls:
                return AgentResult(output=last_text, history=transcript, tool_events=tool_events)

            for tool_call in tool_calls:
                arguments = safe_load_json(tool_call.arguments)
                if on_tool_start is not None:
                    await on_tool_start(tool_call.name, arguments)
                output = await self.tool_bus.dispatch(tool_call.name, arguments)
                if on_tool_end is not None:
                    await on_tool_end(tool_call.name, arguments, output)
                tool_events.append(ToolEvent(tool_call.name, arguments, output))
                transcript.append({"role": "tool", "tool_call_id": tool_call.id, "content": output})

    async def _complete_once(
        self,
        transcript: list[dict[str, Any]],
        on_text_delta: Callable[[str], Awaitable[None]] | None,
    ) -> tuple[str, list[ToolCallData]]:
        kwargs = {
            "model": self.model_name,
            "messages": [{"role": "system", "content": self.system_prompt}, *transcript],
            "tools": self.tool_bus.tool_schemas(),
            "tool_choice": "auto",
            "temperature": self.temperature,
        }
        if on_text_delta is None:
            response = await self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            content = stringify_content(getattr(message, "content", ""))
            tool_calls = [
                ToolCallData(
                    id=call.id,
                    name=call.function.name,
                    arguments=call.function.arguments,
                )
                for call in list(getattr(message, "tool_calls", None) or [])
            ]
            return content, tool_calls

        stream = await self.client.chat.completions.create(stream=True, **kwargs)
        content_parts: list[str] = []
        tool_buffers: dict[int, ToolCallData] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                text = delta.content
                content_parts.append(text)
                await on_text_delta(text)
            for tool_delta in list(getattr(delta, "tool_calls", None) or []):
                index = int(getattr(tool_delta, "index", 0) or 0)
                current = tool_buffers.get(index, ToolCallData(id="", name="", arguments=""))
                call_id = getattr(tool_delta, "id", None) or current.id
                fn = getattr(tool_delta, "function", None)
                name = getattr(fn, "name", None) or current.name
                arguments = current.arguments + (getattr(fn, "arguments", None) or "")
                tool_buffers[index] = ToolCallData(id=call_id, name=name, arguments=arguments)

        tool_calls = [tool_buffers[index] for index in sorted(tool_buffers.keys())]
        return "".join(content_parts), tool_calls


def assistant_message(content: str, tool_calls: list[Any]) -> dict[str, Any]:
    if not tool_calls:
        return {"role": "assistant", "content": content}

    def _tool_name(call: Any) -> str:
        if hasattr(call, "name"):
            return call.name
        function = getattr(call, "function", None)
        return getattr(function, "name", "")

    def _tool_arguments(call: Any) -> str:
        if hasattr(call, "arguments"):
            return call.arguments
        function = getattr(call, "function", None)
        return getattr(function, "arguments", "")

    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": _tool_name(call),
                    "arguments": _tool_arguments(call),
                },
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
