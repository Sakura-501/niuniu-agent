from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI


def should_format_debug_answer(user_input: str, tool_events: list[Any]) -> bool:
    if tool_events:
        return True
    keywords = ("解法", "flag", "总结", "结果", "结论", "思路")
    return any(keyword in user_input for keyword in keywords)


def build_formatter_prompt(user_input: str, raw_output: str, tool_events: list[Any]) -> str:
    tool_lines = []
    for event in tool_events:
        preview = event.output.replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:197] + "..."
        tool_lines.append(
            f"- tool={event.name} args={json.dumps(event.arguments, ensure_ascii=False)} result={preview}"
        )
    tool_text = "\n".join(tool_lines) if tool_lines else "(no tool usage)"
    return (
        "请根据以下调试过程，输出一个简洁、结构化、中文的最终回答。\n"
        "必须尽量使用以下 markdown 小节：\n"
        "## 结论\n## 解法\n## 关键证据\n## Flag\n## 下一步\n"
        "如果没有找到 flag，就明确写“未找到”。\n"
        "不要重复大段原始工具输出，只提炼重点。\n\n"
        f"用户请求：{user_input}\n\n"
        f"原始回答：{raw_output}\n\n"
        f"工具摘要：\n{tool_text}\n"
    )


async def stream_formatted_answer(
    client: AsyncOpenAI,
    model_name: str,
    user_input: str,
    raw_output: str,
    tool_events: list[Any],
    on_text_delta: Callable[[str], Awaitable[None]],
) -> str:
    stream = await client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise pentest result formatter. "
                    "Produce only the final cleaned answer in Chinese markdown."
                ),
            },
            {"role": "user", "content": build_formatter_prompt(user_input, raw_output, tool_events)},
        ],
        temperature=0.2,
        stream=True,
    )

    chunks: list[str] = []
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        text = getattr(delta, "content", None)
        if text:
            chunks.append(text)
            await on_text_delta(text)
    return "".join(chunks)
