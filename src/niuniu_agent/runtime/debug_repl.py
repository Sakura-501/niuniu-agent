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
from niuniu_agent.skills.planner import plan_skills


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


def _is_greeting(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"hi", "hello", "hey", "你好", "您好", "在吗", "在么"}


def _build_greeting_reply(summary: str) -> str:
    return "你好，我已进入调试模式。\n\n当前赛题状态：\n" + summary


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
        if _is_greeting(user_input):
            print(_build_greeting_reply(context.challenge_store.render_summary(snapshot)))
            continue
        active = context.challenge_store.next_candidate(snapshot)
        context.notes["latest_snapshot"] = context.challenge_store.export_json(snapshot)
        runtime_state = (
            context.state_store.get_challenge_runtime_state(active.code)
            if active is not None
            else {}
        )
        notes = context.state_store.get_challenge_notes(active.code) if active is not None else {}
        skill_plan = (
            plan_skills(context.skill_registry, active.description if active else "", runtime_state, notes)
            if context.skill_registry and active is not None
            else None
        )
        agent = AsyncPentestAgent(
            client=client,
            model_name=context.settings.model,
            system_prompt="\n\n".join(
                [
                    build_entry_prompt(
                        "debug",
                        snapshot,
                        active,
                        skill_plan.skills if skill_plan else [],
                        stage=skill_plan.stage if skill_plan else None,
                        runtime_state=runtime_state,
                        notes=notes,
                    ),
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
