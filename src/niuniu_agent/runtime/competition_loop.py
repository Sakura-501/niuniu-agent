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
from niuniu_agent.runtime.manager import CompetitionManagerAgent
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
    manager_context = context.spawn(agent_id="manager:competition", agent_role="manager")
    manager = CompetitionManagerAgent(manager_context, findings_bus)
    refresh_backoff = 1

    async def run_worker(challenge_code: str) -> None:
        worker_context = context.spawn(
            agent_id=f"worker:{challenge_code}",
            agent_role="challenge_worker",
            challenge_code=challenge_code,
        )
        backoff = context.settings.competition_error_backoff_seconds
        try:
            while True:
                snapshot = await worker_context.challenge_store.refresh()
                target = next((item for item in snapshot.challenges if item.code == challenge_code), None)
                if target is None or target.completed:
                    worker_context.state_store.record_challenge_success(challenge_code)
                    worker_context.state_store.upsert_agent_status(
                        agent_id=worker_context.agent_id or f"worker:{challenge_code}",
                        role="challenge_worker",
                        challenge_code=challenge_code,
                        status="completed",
                        summary="challenge completed",
                        metadata={"challenge_code": challenge_code},
                    )
                    return

                worker_context.notes["active_challenge"] = target.code
                worker_context.state_store.mark_active_challenge(target.code)
                runtime_state = worker_context.state_store.get_challenge_runtime_state(target.code)
                notes = worker_context.state_store.get_challenge_notes(target.code)
                seconds_since_progress = worker_context.state_store.seconds_since_progress(target.code)
                if should_view_hint(
                    int(runtime_state.get("failure_count", 0)),
                    target.hint_viewed,
                    notes,
                    seconds_since_progress=seconds_since_progress,
                ):
                    hint_payload = await worker_context.contest_gateway.view_hint(target.code)
                    worker_context.state_store.add_history_event(target.code, "hint_viewed", str(hint_payload))
                    worker_context.state_store.set_challenge_note(target.code, "hint_viewed", "true")
                    notes = worker_context.state_store.get_challenge_notes(target.code)

                skill_plan = (
                    plan_skills(
                        worker_context.skill_registry,
                        target.description,
                        runtime_state,
                        notes,
                        track=infer_track(target.description),
                    )
                    if worker_context.skill_registry
                    else None
                )
                shared_findings = await findings_bus.check(target.code, consumer=f"worker:{target.code}")
                if shared_findings:
                    worker_context.state_store.set_challenge_note(
                        target.code,
                        "shared_findings",
                        findings_bus.format_unread(shared_findings)[:4000],
                    )
                    notes = worker_context.state_store.get_challenge_notes(target.code)
                available_skills = worker_context.skill_registry.describe_available() if worker_context.skill_registry else None
                worker_context.state_store.upsert_agent_status(
                    agent_id=worker_context.agent_id or f"worker:{challenge_code}",
                    role="challenge_worker",
                    challenge_code=target.code,
                    status="running",
                    summary=f"{target.title} / {skill_plan.stage if skill_plan else 'recon'}",
                    metadata={
                        "track": infer_track(target.description),
                        "stage": skill_plan.stage if skill_plan else "recon",
                        "instance_status": target.instance_status,
                    },
                )

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
                                available_skills=available_skills,
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
                    tool_bus=ToolBus(worker_context),
                )
                prompt = worker_context.challenge_store.build_autonomous_prompt(snapshot, target)
                result = await agent.execute(prompt, histories.get(target.code))
                histories[target.code] = result.history
                worker_context.state_store.add_history_event(target.code, "turn_completed", result.output or "")
                if result.output or result.tool_events:
                    worker_context.state_store.mark_progress(target.code)
                for key, value in extract_runtime_notes(
                    result.output,
                    [{"name": event.name, "arguments": event.arguments, "output": event.output} for event in result.tool_events],
                ).items():
                    worker_context.state_store.set_challenge_note(target.code, key, value)
                await findings_bus.post(target.code, source=f"worker:{target.code}", content=(result.output or "")[:1000])
                worker_context.event_logger.log(
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
                worker_context.state_store.record_challenge_success(target.code)
                worker_context.state_store.append_agent_event(
                    agent_id=worker_context.agent_id or f"worker:{challenge_code}",
                    challenge_code=target.code,
                    event_type="worker_turn_completed",
                    payload=(result.output or "")[:1000],
                )
                backoff = context.settings.competition_error_backoff_seconds
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            worker_context.state_store.upsert_agent_status(
                agent_id=worker_context.agent_id or f"worker:{challenge_code}",
                role="challenge_worker",
                challenge_code=challenge_code,
                status="cancelled",
                summary="worker cancelled",
                metadata={"challenge_code": challenge_code},
            )
            raise
        except Exception as exc:  # pragma: no cover - runtime recovery path
            worker_context.notes["last_error"] = str(exc)
            failure_count = worker_context.state_store.record_challenge_failure(challenge_code, str(exc))
            worker_context.state_store.add_history_event(challenge_code, "error", str(exc))
            worker_context.state_store.set_challenge_note(challenge_code, "last_error", str(exc))
            worker_context.state_store.upsert_agent_status(
                agent_id=worker_context.agent_id or f"worker:{challenge_code}",
                role="challenge_worker",
                challenge_code=challenge_code,
                status="error",
                summary="worker failed; waiting for recovery",
                metadata={"challenge_code": challenge_code},
                last_error=str(exc),
            )
            worker_context.state_store.append_agent_event(
                agent_id=worker_context.agent_id or f"worker:{challenge_code}",
                challenge_code=challenge_code,
                event_type="worker_error",
                payload=str(exc),
            )
            worker_context.event_logger.log(
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
            try:
                snapshot = await context.challenge_store.refresh()
                refresh_backoff = 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - runtime recovery path
                context.event_logger.log(
                    "competition.refresh_error",
                    {
                        "error": str(exc),
                        "backoff_seconds": refresh_backoff,
                    },
                )
                manager_context.state_store.upsert_agent_status(
                    agent_id="manager:competition",
                    role="manager",
                    challenge_code=None,
                    status="degraded",
                    summary="challenge refresh failed; retrying",
                    metadata={"backoff_seconds": refresh_backoff},
                    last_error=str(exc),
                )
                await asyncio.sleep(refresh_backoff)
                refresh_backoff = min(refresh_backoff * 2, context.settings.competition_max_error_backoff_seconds)
                continue
            manager.heartbeat(snapshot, coordinator)
            manager.reconcile(coordinator)
            candidates = [challenge.code for challenge in snapshot.challenges if not challenge.completed]

            if not candidates:
                context.event_logger.log("competition.idle", {"reason": "no-open-challenges"})
                await asyncio.sleep(context.settings.competition_idle_sleep_seconds)
                continue

            started = await coordinator.schedule(candidates, run_worker)
            if started:
                await manager.publish_assignment_guidance(snapshot, started)
                context.event_logger.log(
                    "competition.scheduler",
                    {"started": started, "active_count": coordinator.active_count()},
                )
            await asyncio.sleep(2)
    finally:
        await coordinator.stop_all()
