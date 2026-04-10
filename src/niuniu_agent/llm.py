from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from niuniu_agent.tooling import LocalToolbox


@dataclass(slots=True)
class AgentRunResult:
    final_text: str
    tool_events: list[dict[str, Any]] = field(default_factory=list)


class OpenAIToolLoop:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        max_iterations: int = 12,
    ) -> None:
        self.model = model
        self.max_iterations = max_iterations
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def run(self, system_prompt: str, user_prompt: str, toolbox: LocalToolbox) -> AgentRunResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        tool_events: list[dict[str, Any]] = []

        for _ in range(self.max_iterations):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=toolbox.describe_tools(),
                tool_choice="auto",
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return AgentRunResult(final_text=message.content or "", tool_events=tool_events)

            assistant_message = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in message.tool_calls
                ],
            }
            messages.append(assistant_message)

            for tool_call in message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}

                try:
                    result = await toolbox.execute(tool_call.function.name, arguments)
                except Exception as exc:  # pragma: no cover - defensive path for live runs
                    result = {"error": str(exc)}

                tool_events.append(
                    {
                        "tool": tool_call.function.name,
                        "arguments": arguments,
                        "result": result,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=True),
                    }
                )

        return AgentRunResult(
            final_text="Reached maximum tool iterations without a final answer.",
            tool_events=tool_events,
        )
