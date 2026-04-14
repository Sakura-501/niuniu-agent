from __future__ import annotations

import sys

from niuniu_agent.agent_stack.agent import AsyncPentestAgent, build_prompt_cache_key
from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    FLAG_SUBMIT_PROMPT,
    build_entry_prompt,
    build_runtime_instruction,
    build_trigger_prompt,
)
from niuniu_agent.agent_stack.tool_bus import ToolBus
from niuniu_agent.control_plane.challenge_store import compact_challenge_notes
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
        turn_context = context.spawn(
            agent_id="debug:repl",
            agent_role="debug",
            challenge_code=active.code if active is not None else None,
        )
        turn_context.notes["latest_snapshot"] = context.challenge_store.export_json(snapshot)
        runtime_state = (
            turn_context.state_store.get_challenge_runtime_state(active.code)
            if active is not None
            else {}
        )
        notes = compact_challenge_notes(turn_context.state_store.get_challenge_notes(active.code)) if active is not None else {}
        recent_history = turn_context.state_store.list_history(active.code, limit=5) if active is not None else []
        recent_memories = turn_context.state_store.list_challenge_memories(active.code, limit=10) if active is not None else []
        track = infer_track(active.description) if active is not None else None
        skill_plan = (
            plan_skills(turn_context.skill_registry, active.description if active else "", runtime_state, notes, track=track)
            if turn_context.skill_registry and active is not None
            else None
        )
        available_skills = turn_context.skill_registry.describe_available() if turn_context.skill_registry else None
        client = turn_context.provider_router.build_client() if turn_context.provider_router is not None else None
        if client is None:
            raise RuntimeError("model provider router unavailable")
        agent = AsyncPentestAgent(
            client=client,
            model_name=turn_context.settings.model,
            system_prompt="\n\n".join(
                [
                    build_entry_prompt(
                        "debug",
                        None,
                        None,
                        [],
                        available_skills=available_skills,
                        operator_resources={
                            "callback_server": turn_context.settings.callback_resource,
                        }
                        if turn_context.settings.callback_resource
                        else None,
                    ),
                    build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                    build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                ]
            ),
            prompt_cache_key=build_prompt_cache_key(
                "debug",
                turn_context.agent_role or "debug",
                active.code if active is not None else "no-challenge",
                turn_context.settings.model,
                system_prompt="\n\n".join(
                    [
                        build_entry_prompt(
                            "debug",
                            None,
                            None,
                            [],
                            available_skills=available_skills,
                            operator_resources={
                                "callback_server": turn_context.settings.callback_resource,
                            }
                            if turn_context.settings.callback_resource
                            else None,
                        ),
                        build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                        build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                    ]
                ),
            ),
            tool_bus=ToolBus(turn_context),
            workdir=turn_context.settings.runtime_dir,
            context_window_tokens=turn_context.settings.model_context_window_tokens,
            context_compaction_threshold_ratio=turn_context.settings.context_compaction_threshold_ratio,
            estimated_chars_per_token=turn_context.settings.estimated_chars_per_token,
            context_compaction_keep_tail_messages=turn_context.settings.context_compaction_keep_tail_messages,
            context_compaction_keep_recent_tool_results=turn_context.settings.context_compaction_keep_recent_tool_results,
            context_compaction_tool_result_preview_chars=turn_context.settings.context_compaction_tool_result_preview_chars,
            context_compaction_summary_input_chars=turn_context.settings.context_compaction_summary_input_chars,
            context_compaction_summary_max_tokens=turn_context.settings.context_compaction_summary_max_tokens,
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
            build_runtime_instruction(
                mode="debug",
                user_input=user_input,
                snapshot=snapshot,
                active=active,
                runtime_state=runtime_state,
                notes=notes,
                recent_history=recent_history,
                recent_memories=recent_memories,
                selected_skills=skill_plan.skills if skill_plan else [],
                available_skills=available_skills,
                stage=skill_plan.stage if skill_plan else None,
                track=track,
                summary_request=_is_summary_request(user_input),
                operator_resources={
                    "callback_server": turn_context.settings.callback_resource,
                }
                if turn_context.settings.callback_resource
                else None,
            ),
            history,
            on_text_delta=on_text_delta,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        )
        history = result.history
        raw_output = result.output or "".join(buffered_text_chunks)
        turn_context.state_store.upsert_agent_status(
            agent_id=turn_context.agent_id or "debug:repl",
            role="debug",
            challenge_code=turn_context.challenge_code,
            status="idle",
            summary=(raw_output or user_input)[:240],
            metadata={"summary_request": _is_summary_request(user_input)},
        )
        turn_context.state_store.append_agent_event(
            agent_id=turn_context.agent_id or "debug:repl",
            challenge_code=turn_context.challenge_code,
            event_type="debug_turn_completed",
            payload=raw_output[:1000] if raw_output else user_input,
        )

        if should_format_debug_answer(user_input, result.tool_events):
            printed_final = False

            async def on_final_delta(text: str) -> None:
                nonlocal printed_final
                print(text, end="", flush=True)
                printed_final = True

            final_output = await stream_formatted_answer(
                client=client,
                model_name=turn_context.settings.model,
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
