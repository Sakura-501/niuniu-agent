from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from niuniu_agent.agent_stack.agent import AsyncPentestAgent
from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    FLAG_SUBMIT_PROMPT,
    HINT_DECISION_PROMPT,
    PRE_EXPLOIT_PROMPT,
    RECOVERY_PROMPT,
    build_entry_prompt,
    build_trigger_prompt,
)
from niuniu_agent.agent_stack.tool_bus import ToolBus
from niuniu_agent.runtime.coordinator import CompetitionCoordinator
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.findings_bus import ChallengeFindingsBus
from niuniu_agent.runtime.recovery import extract_runtime_notes, should_view_hint
from niuniu_agent.skills.planner import plan_skills
from niuniu_agent.skills.tracks import infer_track


async def run_competition_loop(context: RuntimeContext) -> None:
    client = AsyncOpenAI(
        api_key=context.settings.model_api_key,
        base_url=context.settings.model_base_url,
    )
    histories: dict[str, list[dict[str, object]]] = {}
    findings_bus = ChallengeFindingsBus()
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)

    async def run_worker(challenge_code: str) -> None:
        backoff = context.settings.competition_error_backoff_seconds
        try:
            while True:
                snapshot = await context.challenge_store.refresh()
                target = next((item for item in snapshot.challenges if item.code == challenge_code), None)
                if target is None or target.completed:
                    context.state_store.record_challenge_success(challenge_code)
                    return

                context.notes["active_challenge"] = target.code
                context.state_store.mark_active_challenge(target.code)
                runtime_state = context.state_store.get_challenge_runtime_state(target.code)
                notes = context.state_store.get_challenge_notes(target.code)
                seconds_since_progress = context.state_store.seconds_since_progress(target.code)
                if should_view_hint(
                    int(runtime_state.get("failure_count", 0)),
                    target.hint_viewed,
                    notes,
                    seconds_since_progress=seconds_since_progress,
                ):
                    hint_payload = await context.contest_gateway.view_hint(target.code)
                    context.state_store.add_history_event(target.code, "hint_viewed", str(hint_payload))
                    context.state_store.set_challenge_note(target.code, "hint_viewed", "true")
                    notes = context.state_store.get_challenge_notes(target.code)

                skill_plan = (
                    plan_skills(
                        context.skill_registry,
                        target.description,
                        runtime_state,
                        notes,
                        track=infer_track(target.description),
                    )
                    if context.skill_registry
                    else None
                )
                shared_findings = await findings_bus.check(target.code, consumer=f"worker:{target.code}")
                if shared_findings:
                    context.state_store.set_challenge_note(
                        target.code,
                        "shared_findings",
                        findings_bus.format_unread(shared_findings)[:4000],
                    )
                    notes = context.state_store.get_challenge_notes(target.code)

                agent = AsyncPentestAgent(
                    client=client,
                    model_name=context.settings.model,
                    system_prompt="\n\n".join(
                        [
                            build_entry_prompt(
                                "competition",
                                snapshot,
                                target,
                                skill_plan.skills if skill_plan else [],
                                stage=skill_plan.stage if skill_plan else None,
                                runtime_state=runtime_state,
                                notes=notes,
                                track=infer_track(target.description),
                            ),
                            build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                            build_trigger_prompt(PRE_EXPLOIT_PROMPT),
                            build_trigger_prompt(RECOVERY_PROMPT) if int(runtime_state.get("failure_count", 0)) > 0 else "",
                            build_trigger_prompt(HINT_DECISION_PROMPT) if notes.get("hint_viewed") == "true" else "",
                            build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                        ]
                    ),
                    tool_bus=ToolBus(context),
                )
                prompt = context.challenge_store.build_autonomous_prompt(snapshot, target)
                result = await agent.execute(prompt, histories.get(target.code))
                histories[target.code] = result.history
                context.state_store.add_history_event(target.code, "turn_completed", result.output or "")
                if result.output or result.tool_events:
                    context.state_store.mark_progress(target.code)
                for key, value in extract_runtime_notes(
                    result.output,
                    [{"name": event.name, "arguments": event.arguments, "output": event.output} for event in result.tool_events],
                ).items():
                    context.state_store.set_challenge_note(target.code, key, value)
                await findings_bus.post(target.code, source=f"worker:{target.code}", content=(result.output or "")[:1000])
                context.event_logger.log(
                    "competition.turn_completed",
                    {
                        "challenge_code": target.code,
                        "output": result.output,
                        "tool_events": [
                            {"name": event.name, "arguments": event.arguments, "output": event.output}
                            for event in result.tool_events
                        ],
                    },
                )
                context.state_store.record_challenge_success(target.code)
                backoff = context.settings.competition_error_backoff_seconds
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - runtime recovery path
            context.notes["last_error"] = str(exc)
            failure_count = context.state_store.record_challenge_failure(challenge_code, str(exc))
            context.state_store.add_history_event(challenge_code, "error", str(exc))
            context.state_store.set_challenge_note(challenge_code, "last_error", str(exc))
            context.event_logger.log(
                "competition.error",
                {
                    "error": str(exc),
                    "backoff_seconds": backoff,
                    "active_challenge": challenge_code,
                    "failure_count": failure_count,
                    "recovery_prompt": build_trigger_prompt(RECOVERY_PROMPT),
                },
            )
            await asyncio.sleep(backoff)
            # Let outer coordinator reschedule this challenge again
            raise

    try:
        while True:
            snapshot = await context.challenge_store.refresh()
            candidates = [challenge.code for challenge in snapshot.challenges if not challenge.completed]

            if not candidates:
                context.event_logger.log("competition.idle", {"reason": "no-open-challenges"})
                await asyncio.sleep(context.settings.competition_idle_sleep_seconds)
                continue

            started = await coordinator.schedule(candidates, run_worker)
            if started:
                context.event_logger.log(
                    "competition.scheduler",
                    {"started": started, "active_count": coordinator.active_count()},
                )
            await asyncio.sleep(2)
    finally:
        await coordinator.stop_all()
