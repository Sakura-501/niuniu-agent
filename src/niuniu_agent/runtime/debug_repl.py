from __future__ import annotations

import sys

from openai import AsyncOpenAI

from niuniu_agent.agent_stack.agent import AsyncPentestAgent
from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    FLAG_SUBMIT_PROMPT,
    build_entry_prompt,
    build_trigger_prompt,
)
from niuniu_agent.agent_stack.tool_bus import ToolBus
from niuniu_agent.runtime.context import RuntimeContext


def _decode_user_input(raw: bytes) -> str:
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding).rstrip("\r\n")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").rstrip("\r\n")


def _read_line(prompt: str = "debug") -> str:
    print(f"{prompt}: ", end="", flush=True)
    raw = sys.stdin.buffer.readline()
    if raw == b"":
        return "exit"
    return _decode_user_input(raw)


async def run_debug_repl(context: RuntimeContext) -> None:
    client = AsyncOpenAI(
        api_key=context.settings.model_api_key,
        base_url=context.settings.model_base_url,
    )
    history: list[dict[str, object]] = []

    print("已进入重构后的 debug 交互模式。输入 exit 或 quit 退出。")
    snapshot = await context.challenge_store.refresh()
    print(context.challenge_store.render_summary(snapshot))

    while True:
        user_input = _read_line("debug")
        if user_input.strip().lower() in {"exit", "quit", "/exit", "/quit"}:
            break

        snapshot = await context.challenge_store.refresh()
        active = context.challenge_store.next_candidate(snapshot)
        context.notes["latest_snapshot"] = context.challenge_store.export_json(snapshot)
        skills = context.skill_registry.select(active.description if active else "", track=None) if context.skill_registry else []
        agent = AsyncPentestAgent(
            client=client,
            model_name=context.settings.model,
            system_prompt="\n\n".join(
                [
                    build_entry_prompt("debug", snapshot, active, skills),
                    build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                    build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                ]
            ),
            tool_bus=ToolBus(context),
        )
        result = await agent.execute(user_input, history)
        history = result.history
        for event in result.tool_events:
            print(f"[tool] {event.name}")
            print(f"  args: {event.arguments}")
            print(f"  result: {event.output[:240]}")
        print(result.output or "[assistant produced no text]")
