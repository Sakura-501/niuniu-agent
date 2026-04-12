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
        context_window_tokens: int = 204800,
        context_compaction_threshold_ratio: float = 0.8,
        estimated_chars_per_token: int = 4,
        context_compaction_keep_tail_messages: int = 8,
        context_compaction_keep_recent_tool_results: int = 3,
        context_compaction_tool_result_preview_chars: int = 240,
        context_compaction_summary_input_chars: int = 80000,
        context_compaction_summary_max_tokens: int = 2000,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.tool_bus = tool_bus
        self.workdir = Path(workdir or Path.cwd()).resolve()
        self.temperature = temperature
        self.context_window_tokens = context_window_tokens
        self.context_compaction_threshold_ratio = context_compaction_threshold_ratio
        self.estimated_chars_per_token = estimated_chars_per_token
        self.context_compaction_keep_tail_messages = context_compaction_keep_tail_messages
        self.context_compaction_keep_recent_tool_results = context_compaction_keep_recent_tool_results
        self.context_compaction_tool_result_preview_chars = context_compaction_tool_result_preview_chars
        self.context_compaction_summary_input_chars = context_compaction_summary_input_chars
        self.context_compaction_summary_max_tokens = context_compaction_summary_max_tokens

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
            transcript = await self._maybe_compact_transcript(transcript)
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

    async def _maybe_compact_transcript(self, transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self._estimate_context_chars(transcript) <= self._context_threshold_chars():
            return transcript
        compacted = self._micro_compact_tool_results(transcript)
        if self._estimate_context_chars(compacted) <= self._context_threshold_chars():
            return compacted
        if len(compacted) <= self.context_compaction_keep_tail_messages:
            return compacted
        summary_source = compacted[:-self.context_compaction_keep_tail_messages]
        recent_tail = compacted[-self.context_compaction_keep_tail_messages :]
        summary = await self._summarize_history(summary_source)
        return [
            {
                "role": "user",
                "content": (
                    "This conversation was replaced by automatic context compaction.\n\n"
                    f"{summary}"
                ),
            },
            *recent_tail,
        ]

    def _micro_compact_tool_results(self, transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tool_indexes = [index for index, message in enumerate(transcript) if message.get("role") == "tool"]
        if len(tool_indexes) <= self.context_compaction_keep_recent_tool_results:
            return transcript
        compacted = [dict(message) for message in transcript]
        for index in tool_indexes[:-self.context_compaction_keep_recent_tool_results]:
            content = compacted[index].get("content")
            if not isinstance(content, str):
                continue
            if len(content) <= self.context_compaction_tool_result_preview_chars:
                continue
            compacted[index]["content"] = (
                "[Older tool result compacted. Refer to persisted challenge history/memory or rerun the tool if needed.]"
            )
        return compacted

    async def _summarize_history(self, transcript: list[dict[str, Any]]) -> str:
        serialized = json.dumps(transcript, ensure_ascii=False, default=str)
        prompt = (
            "Summarize this pentest-agent conversation so work can continue after automatic context compaction.\n"
            "Preserve:\n"
            "1. Current objective and active challenge\n"
            "2. Important findings, failed paths, and decisions\n"
            "3. Tools already used and what they proved\n"
            "4. Files, endpoints, credentials, flags, or hosts worth revisiting\n"
            "5. Remaining next steps\n\n"
            f"{serialized[: self.context_compaction_summary_input_chars]}"
        )
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize pentest agent context compactly so work can continue without losing critical facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=self.context_compaction_summary_max_tokens,
        )
        message = response.choices[0].message
        return stringify_content(getattr(message, "content", "")) or "(summary unavailable)"

    def _context_threshold_chars(self) -> int:
        return int(
            self.context_window_tokens
            * self.context_compaction_threshold_ratio
            * self.estimated_chars_per_token
        )

    def _estimate_context_chars(self, transcript: list[dict[str, Any]]) -> int:
        payload = {
            "system": self.system_prompt,
            "messages": transcript,
            "tools": self.tool_bus.tool_schemas(),
        }
        return len(json.dumps(payload, ensure_ascii=False, default=str))


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
