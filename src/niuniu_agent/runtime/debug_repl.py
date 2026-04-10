from __future__ import annotations

import sys

from agents import Runner, SQLiteSession

from niuniu_agent.agent_stack.factory import build_agent_assembly
from niuniu_agent.runtime.agent_loop import run_until_final_output
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.hooks import RuntimeTraceHooks, TraceRecorder


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
    assembly = build_agent_assembly(context.settings)
    session = SQLiteSession(
        session_id="debug-repl",
        db_path=context.settings.session_db_path,
    )

    await assembly.contest_server.connect()
    try:
        print("已进入重构后的 debug 交互模式。输入 exit 或 quit 退出。")
        snapshot = await context.challenge_store.refresh()
        print(context.challenge_store.render_summary(snapshot))

        while True:
            user_input = _read_line("debug")
            if user_input.strip().lower() in {"exit", "quit", "/exit", "/quit"}:
                break

            snapshot = await context.challenge_store.refresh()
            context.notes["latest_snapshot"] = context.challenge_store.export_json(snapshot)

            recorder = TraceRecorder()
            hooks = RuntimeTraceHooks(recorder, context.event_logger)
            result = await run_until_final_output(
                assembly.manager,
                initial_input=user_input,
                context=context,
                hooks=hooks,
                session=session,
                event_logger=context.event_logger,
            )

            if recorder.events:
                print(recorder.render())
            print(result.final_output_as(str))
    finally:
        await assembly.contest_server.cleanup()
