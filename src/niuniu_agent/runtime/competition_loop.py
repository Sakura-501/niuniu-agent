from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from niuniu_agent.agent_stack.agent import AsyncPentestAgent
from niuniu_agent.agent_stack.prompts import build_system_prompt
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
            agent = AsyncPentestAgent(
                client=client,
                model_name=context.settings.model,
                system_prompt=build_system_prompt("competition", snapshot, challenge),
                tool_bus=ToolBus(context),
            )
            prompt = context.challenge_store.build_autonomous_prompt(snapshot, challenge)
            result = await agent.execute(prompt, histories.get(challenge.code))
            histories[challenge.code] = result.history
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
