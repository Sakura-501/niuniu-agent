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
from niuniu_agent.runtime.answer_formatter import should_format_debug_answer, stream_formatted_answer
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.skills.planner import plan_skills
from niuniu_agent.skills.tracks import infer_track


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


def _is_summary_request(text: str) -> bool:
    keywords = ("总结", "解法", "flag", "结果", "结论", "当前情况", "情况", "思路")
    return any(keyword in text for keyword in keywords)


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
        runtime_state = (
            context.state_store.get_challenge_runtime_state(active.code)
            if active is not None
            else {}
        )
        notes = context.state_store.get_challenge_notes(active.code) if active is not None else {}
        track = infer_track(active.description) if active is not None else None
        skill_plan = (
            plan_skills(context.skill_registry, active.description if active else "", runtime_state, notes, track=track)
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
                        summary_request=_is_summary_request(user_input),
                        track=track,
                    ),
                    build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                    build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                ]
            ),
            tool_bus=ToolBus(context),
        )
        buffered_text_chunks: list[str] = []

        async def on_text_delta(text: str) -> None:
            buffered_text_chunks.append(text)

        async def on_tool_start(name: str, arguments: dict[str, object]) -> None:
            print(f"\n[tool:start] {name} {arguments}", flush=True)

        async def on_tool_end(name: str, arguments: dict[str, object], output: str) -> None:
            preview = output.replace("\n", " ")
            if len(preview) > 160:
                preview = preview[:157] + "..."
            print(f"[tool:done] {name} -> {preview}", flush=True)

        result = await agent.execute_stream(
            user_input,
            history,
            on_text_delta=on_text_delta,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        )
        history = result.history
        raw_output = result.output or "".join(buffered_text_chunks)

        if should_format_debug_answer(user_input, result.tool_events):
            printed_final = False

            async def on_final_delta(text: str) -> None:
                nonlocal printed_final
                print(text, end="", flush=True)
                printed_final = True

            final_output = await stream_formatted_answer(
                client=client,
                model_name=context.settings.model,
                user_input=user_input,
                raw_output=raw_output,
                tool_events=result.tool_events,
                on_text_delta=on_final_delta,
            )
            if printed_final:
                print()
            elif final_output:
                print(final_output)
            else:
                print("[assistant produced no text]")
        else:
            if raw_output:
                print(raw_output)
            else:
                print("[assistant produced no text]")
