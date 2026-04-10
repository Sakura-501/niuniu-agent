from __future__ import annotations

import asyncio

from agents import Runner, SQLiteSession

from niuniu_agent.agent_stack.factory import build_agent_assembly
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.hooks import RuntimeTraceHooks, TraceRecorder


async def run_competition_loop(context: RuntimeContext) -> None:
    assembly = build_agent_assembly(context.settings)
    backoff = context.settings.competition_error_backoff_seconds

    await assembly.contest_server.connect()
    try:
        while True:
            try:
                snapshot = await context.challenge_store.refresh()
                challenge = context.challenge_store.next_candidate(snapshot)

                if challenge is None:
                    context.event_logger.log("competition.idle", {"reason": "no-open-challenges"})
                    await asyncio.sleep(context.settings.competition_idle_sleep_seconds)
                    continue

                session = SQLiteSession(
                    session_id=f"competition-{challenge.code}",
                    db_path=context.settings.session_db_path,
                )
                context.notes["active_challenge"] = challenge.code
                recorder = TraceRecorder()
                hooks = RuntimeTraceHooks(recorder, context.event_logger)
                prompt = context.challenge_store.build_autonomous_prompt(snapshot, challenge)

                result = await Runner.run(
                    assembly.manager,
                    prompt,
                    context=context,
                    max_turns=context.settings.agent_max_turns,
                    hooks=hooks,
                    session=session,
                )
                context.event_logger.log(
                    "competition.turn_completed",
                    {
                        "challenge_code": challenge.code,
                        "output": result.final_output_as(str),
                        "trace": recorder.render(),
                    },
                )
                backoff = context.settings.competition_error_backoff_seconds
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - runtime recovery path
                context.event_logger.log(
                    "competition.error",
                    {
                        "error": str(exc),
                        "backoff_seconds": backoff,
                    },
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, context.settings.competition_max_error_backoff_seconds)
    finally:
        await assembly.contest_server.cleanup()
