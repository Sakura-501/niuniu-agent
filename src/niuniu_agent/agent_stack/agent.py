from __future__ import annotations

import hashlib
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


def build_prompt_cache_key(*parts: object, system_prompt: str, max_length: int = 180) -> str:
    normalized_parts = [
        "".join(ch if ch.isalnum() or ch in {"-", "_", ":"} else "-" for ch in str(part).strip())
        for part in parts
        if str(part).strip()
    ]
    prefix = ":".join(part[:48] for part in normalized_parts if part)[:120]
    digest = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]
    if prefix:
        return f"{prefix}:{digest}"[:max_length]
    return digest


class AsyncPentestAgent:
    def __init__(
        self,
        client: AsyncOpenAI,
        model_name: str,
        system_prompt: str,
        tool_bus: Any,
        workdir: Path | str | None = None,
        temperature: float = 0.2,
        context_window_tokens: int = 256000,
        context_compaction_threshold_ratio: float = 0.9,
        estimated_chars_per_token: int = 4,
        context_compaction_keep_tail_messages: int = 8,
        context_compaction_keep_recent_tool_results: int = 3,
        context_compaction_tool_result_preview_chars: int = 240,
        context_compaction_summary_input_chars: int = 80000,
        context_compaction_summary_max_tokens: int = 2000,
        prompt_cache_key: str | None = None,
        prompt_cache_retention: str | None = None,
        session_logger: Any | None = None,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.tool_bus = tool_bus
        self.workdir = Path(workdir or Path.cwd()).resolve()
        self.temperature = temperature
        self._system_message = {"role": "system", "content": self.system_prompt}
        self._tool_schemas = self.tool_bus.tool_schemas()
        self.context_window_tokens = context_window_tokens
        self.context_compaction_threshold_ratio = context_compaction_threshold_ratio
        self.estimated_chars_per_token = estimated_chars_per_token
        self.context_compaction_keep_tail_messages = context_compaction_keep_tail_messages
        self.context_compaction_keep_recent_tool_results = context_compaction_keep_recent_tool_results
        self.context_compaction_tool_result_preview_chars = context_compaction_tool_result_preview_chars
        self.context_compaction_summary_input_chars = context_compaction_summary_input_chars
        self.context_compaction_summary_max_tokens = context_compaction_summary_max_tokens
        self.prompt_cache_key = prompt_cache_key
        self.prompt_cache_retention = prompt_cache_retention or ("24h" if prompt_cache_key else None)
        self._prompt_cache_supported = True
        self.session_logger = session_logger

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
        if self.session_logger is not None:
            self.session_logger.start(model_name=self.model_name, system_prompt=self.system_prompt)
            self.session_logger.replay_history(transcript)
            self.session_logger.log_user(instruction)
        transcript.append({"role": "user", "content": instruction})
        tool_events: list[ToolEvent] = []
        last_text = ""

        while True:
            transcript = await self._maybe_compact_transcript(transcript)
            content, tool_calls = await self._complete_once(transcript, on_text_delta=on_text_delta)
            last_text = content or last_text
            if self.session_logger is not None:
                self.session_logger.log_assistant(
                    content,
                    tool_calls=[
                        {"id": call.id, "name": call.name, "arguments": call.arguments}
                        for call in tool_calls
                    ]
                    or None,
                )
            transcript.append(assistant_message(content, tool_calls))
            if not tool_calls:
                return AgentResult(output=last_text, history=transcript, tool_events=tool_events)

            for tool_call in tool_calls:
                arguments = safe_load_json(tool_call.arguments)
                if self.session_logger is not None:
                    self.session_logger.log_tool_call(tool_call.name, arguments)
                if on_tool_start is not None:
                    await on_tool_start(tool_call.name, arguments)
                output = await self.tool_bus.dispatch(tool_call.name, arguments)
                if self.session_logger is not None:
                    self.session_logger.log_tool_result(tool_call.name, output)
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
            "messages": [self._system_message, *transcript],
            "tools": self._tool_schemas,
            "tool_choice": "auto",
            "temperature": self.temperature,
        }
        if self._prompt_cache_supported and self.prompt_cache_key:
            kwargs["prompt_cache_key"] = self.prompt_cache_key
            if self.prompt_cache_retention:
                kwargs["prompt_cache_retention"] = self.prompt_cache_retention
        if on_text_delta is None:
            response = await self._create_with_cache_fallback(kwargs)
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

        kwargs["stream"] = True
        stream = await self._create_with_cache_fallback(kwargs)
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

    async def _create_with_cache_fallback(self, kwargs: dict[str, Any]) -> Any:
        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            if not self._prompt_cache_supported or not self._is_prompt_cache_unsupported_error(str(exc)):
                raise
            self._prompt_cache_supported = False
            retry_kwargs = dict(kwargs)
            retry_kwargs.pop("prompt_cache_key", None)
            retry_kwargs.pop("prompt_cache_retention", None)
            return await self.client.chat.completions.create(**retry_kwargs)

    @staticmethod
    def _is_prompt_cache_unsupported_error(message: str) -> bool:
        lowered = message.lower()
        return (
            "prompt_cache_key" in lowered
            or "prompt_cache_retention" in lowered
            or ("unknown" in lowered and "cache" in lowered)
            or ("unexpected" in lowered and "cache" in lowered)
            or ("extra inputs are not permitted" in lowered and "cache" in lowered)
        )

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
        if self.session_logger is not None:
            self.session_logger.log_compaction_start(
                source_message_count=len(summary_source),
                kept_tail_count=len(recent_tail),
            )
        summary = await self._summarize_history(summary_source)
        if self.session_logger is not None:
            self.session_logger.log_compaction_summary(summary)
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
        return transcript

    async def _summarize_history(self, transcript: list[dict[str, Any]]) -> str:
        prompt = (
            "<system-reminder>\n"
            "Automatic context compaction request. Summarize the existing conversation so work can continue.\n"
            "Preserve:\n"
            "1. Current objective and active challenge\n"
            "2. Important findings, failed paths, and decisions\n"
            "3. Tools already used and what they proved\n"
            "4. Files, endpoints, credentials, flags, or hosts worth revisiting\n"
            "5. Remaining next steps\n"
            "Do not call any tools.\n"
            "</system-reminder>"
        )
        kwargs = {
            "model": self.model_name,
            "messages": [self._system_message, *transcript, {"role": "user", "content": prompt}],
            "tools": self._tool_schemas,
            "tool_choice": "none",
            "temperature": 0.2,
            "max_tokens": self.context_compaction_summary_max_tokens,
        }
        if self._prompt_cache_supported and self.prompt_cache_key:
            kwargs["prompt_cache_key"] = self.prompt_cache_key
            if self.prompt_cache_retention:
                kwargs["prompt_cache_retention"] = self.prompt_cache_retention
        response = await self._create_with_cache_fallback(kwargs)
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
            "tools": self._tool_schemas,
        }
        return len(json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True))


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
