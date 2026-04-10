from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from niuniu_agent.agent_stack.agent import AsyncPentestAgent
from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    FLAG_SUBMIT_PROMPT,
    PRE_EXPLOIT_PROMPT,
    RECOVERY_PROMPT,
    build_entry_prompt,
    build_trigger_prompt,
)
from niuniu_agent.agent_stack.tool_bus import ToolBus
from niuniu_agent.runtime.context import RuntimeContext


async def run_competition_loop(context: RuntimeContext) -> None:
    client = AsyncOpenAI(
        api_key=context.settings.model_api_key,
        base_url=context.settings.model_base_url,
    )
    histories: dict[str, list[dict[str, object]]] = {}
    backoff = context.settings.competition_error_backoff_seconds

    while True:
        try:
            snapshot = await context.challenge_store.refresh()
            challenge = context.challenge_store.next_candidate(snapshot)

            if challenge is None:
                context.event_logger.log("competition.idle", {"reason": "no-open-challenges"})
                await asyncio.sleep(context.settings.competition_idle_sleep_seconds)
                continue

            context.notes["active_challenge"] = challenge.code
            context.state_store.mark_active_challenge(challenge.code)
            skills = context.skill_registry.select(challenge.description, track=None) if context.skill_registry else []
            agent = AsyncPentestAgent(
                client=client,
                model_name=context.settings.model,
                system_prompt="\n\n".join(
                    [
                        build_entry_prompt("competition", snapshot, challenge, skills),
                        build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                        build_trigger_prompt(PRE_EXPLOIT_PROMPT),
                        build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                    ]
                ),
                tool_bus=ToolBus(context),
            )
            prompt = context.challenge_store.build_autonomous_prompt(snapshot, challenge)
            result = await agent.execute(prompt, histories.get(challenge.code))
            histories[challenge.code] = result.history
            context.state_store.add_history_event(challenge.code, "turn_completed", result.output or "")
            if result.output:
                context.state_store.set_challenge_note(challenge.code, "last_output", result.output[:2000])
            context.event_logger.log(
                "competition.turn_completed",
                {
                    "challenge_code": challenge.code,
                    "output": result.output,
                    "tool_events": [
                        {"name": event.name, "arguments": event.arguments, "output": event.output}
                        for event in result.tool_events
                    ],
                },
            )
            context.state_store.record_challenge_success(challenge.code)
            backoff = context.settings.competition_error_backoff_seconds
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - runtime recovery path
            context.notes["last_error"] = str(exc)
            active_challenge = context.notes.get("active_challenge")
            failure_count = None
            if isinstance(active_challenge, str):
                failure_count = context.state_store.record_challenge_failure(active_challenge, str(exc))
                context.state_store.add_history_event(active_challenge, "error", str(exc))
                context.state_store.set_challenge_note(active_challenge, "last_error", str(exc))
            context.event_logger.log(
                "competition.error",
                {
                    "error": str(exc),
                    "backoff_seconds": backoff,
                    "active_challenge": active_challenge,
                    "failure_count": failure_count,
                    "recovery_prompt": build_trigger_prompt(RECOVERY_PROMPT),
                },
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, context.settings.competition_max_error_backoff_seconds)
