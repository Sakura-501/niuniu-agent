from __future__ import annotations

import asyncio
import time
from uuid import uuid4

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
from niuniu_agent.control_plane.challenge_store import compact_challenge_notes
from niuniu_agent.runtime.coordinator import CompetitionCoordinator
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.runtime.findings_bus import ChallengeFindingsBus
from niuniu_agent.runtime.manager import (
    CompetitionManagerAgent,
    has_alternative_unfinished_challenges,
    has_unstarted_dispatchable_challenges,
    partition_dispatchable_challenges,
)
from niuniu_agent.runtime.recovery import extract_runtime_notes, recover_competition_state, should_view_hint
from niuniu_agent.skills.planner import plan_skills
from niuniu_agent.skills.tracks import infer_track


def build_manager_agent_id(run_id: str) -> str:
    return f"manager:competition:{run_id}"


def build_worker_agent_id(challenge_code: str) -> str:
    return f"worker:{challenge_code}:{uuid4().hex[:8]}"


async def stop_challenge_instance_before_worker_exit(
    *,
    contest_gateway: object,
    challenge_code: str,
    instance_status: str | None,
    event_logger: object | None,
    reason: str,
) -> bool:
    if instance_status == "stopped":
        return False
    try:
        await contest_gateway.stop_challenge(challenge_code)
        return True
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        message = str(exc)
        if event_logger is not None and "未运行" not in message and "not running" not in message.lower():
            event_logger.log(
                "competition.worker_exit_stop_failed",
                {"challenge_code": challenge_code, "reason": reason, "error": message},
            )
        return False


async def ensure_challenge_instance_running(
    *,
    contest_gateway: object,
    challenge: object,
    event_logger: object | None,
) -> bool:
    if getattr(challenge, "completed", False):
        return False
    if getattr(challenge, "instance_status", None) == "running":
        return False
    try:
        await contest_gateway.start_challenge(challenge.code)
        return True
    except Exception as exc:  # pragma: no cover - best-effort recovery
        if event_logger is not None:
            event_logger.log(
                "competition.instance_start_failed",
                {"challenge_code": challenge.code, "error": str(exc)},
            )
        return False


async def ensure_worker_target_instance_ready(
    *,
    worker_context: RuntimeContext,
    target: object,
    worker_agent_id: str,
    competition_run_id: str,
    manager_agent_id: str,
) -> tuple[object, bool]:
    if getattr(target, "completed", False) or getattr(target, "instance_status", None) == "running":
        return target, True

    await ensure_challenge_instance_running(
        contest_gateway=worker_context.contest_gateway,
        challenge=target,
        event_logger=worker_context.event_logger,
    )
    snapshot = await worker_context.challenge_store.refresh()
    refreshed = next((item for item in snapshot.challenges if item.code == target.code), target)
    if getattr(refreshed, "completed", False) or getattr(refreshed, "instance_status", None) == "running":
        return refreshed, True

    worker_context.state_store.upsert_agent_status(
        agent_id=worker_context.agent_id or worker_agent_id,
        role="challenge_worker",
        challenge_code=target.code,
        status="waiting_instance",
        summary="waiting for challenge instance to become runnable",
        metadata={
            "challenge_code": target.code,
            "competition_run_id": competition_run_id,
            "manager_agent_id": manager_agent_id,
            "instance_status": getattr(refreshed, "instance_status", None),
        },
    )
    worker_context.state_store.append_agent_event(
        agent_id=worker_context.agent_id or worker_agent_id,
        challenge_code=target.code,
        event_type="worker_waiting_instance",
        payload="instance not running after start attempt; retrying later",
    )
    return refreshed, False


async def recover_stalled_workers(
    *,
    snapshot: object,
    context: RuntimeContext,
    coordinator: CompetitionCoordinator,
    stall_seconds: int,
    now: float | None = None,
) -> list[dict[str, object]]:
    current = time.time() if now is None else now
    recovered: list[dict[str, object]] = []
    for status in context.state_store.list_agent_statuses(role="challenge_worker"):
        if status.get("status") != "running":
            continue
        challenge_code = str(status.get("challenge_code") or "")
        if not challenge_code or not coordinator.is_running(challenge_code):
            continue
        activity = context.state_store.get_agent_last_activity(str(status["agent_id"]))
        if activity is None:
            continue
        stale_for = current - activity
        if stale_for < stall_seconds:
            continue
        metadata = dict(status.get("metadata") or {})
        metadata["recovery_reason"] = f"stalled for {int(stale_for)}s without worker activity"
        context.state_store.upsert_agent_status(
            agent_id=str(status["agent_id"]),
            role="challenge_worker",
            challenge_code=challenge_code,
            status="waiting_recovery",
            summary="stalled worker cancelled; waiting for reschedule",
            metadata=metadata,
            last_error=str(status.get("last_error") or ""),
        )
        context.state_store.append_agent_event(
            agent_id=str(status["agent_id"]),
            challenge_code=challenge_code,
            event_type="worker_stalled",
            payload=metadata["recovery_reason"],
        )
        await coordinator.cancel_worker(challenge_code)
        recovered.append(
            {
                "agent_id": str(status["agent_id"]),
                "challenge_code": challenge_code,
                "stale_for_seconds": int(stale_for),
            }
        )
    return recovered


async def close_completed_challenge_instances(
    *,
    snapshot: object,
    context: RuntimeContext,
) -> list[str]:
    closed: list[str] = []
    for challenge in getattr(snapshot, "challenges", []):
        if not context.challenge_store.is_effectively_completed(challenge):
            continue
        if getattr(challenge, "instance_status", None) != "running":
            continue
        try:
            await context.contest_gateway.stop_challenge(challenge.code)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            context.event_logger.log(
                "competition.completed_instance_close_failed",
                {"challenge_code": challenge.code, "error": str(exc)},
            )
            continue
        context.state_store.record_challenge_success(challenge.code)
        context.state_store.add_history_event(challenge.code, "instance_stopped", "completed challenge instance closed")
        closed.append(challenge.code)
    return closed


async def close_orphaned_challenge_instances(
    *,
    snapshot: object,
    context: RuntimeContext,
    coordinator: CompetitionCoordinator,
) -> list[str]:
    closed: list[str] = []
    for challenge in getattr(snapshot, "challenges", []):
        if getattr(challenge, "instance_status", None) != "running":
            continue
        if context.challenge_store.is_effectively_completed(challenge):
            continue
        if coordinator.is_running(challenge.code):
            continue
        try:
            await context.contest_gateway.stop_challenge(challenge.code)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            context.event_logger.log(
                "competition.orphaned_instance_close_failed",
                {"challenge_code": challenge.code, "error": str(exc)},
            )
            continue
        context.state_store.add_history_event(
            challenge.code,
            "instance_stopped",
            "orphaned challenge instance closed by manager cleanup",
        )
        closed.append(challenge.code)
    return closed


async def retire_completed_workers(
    *,
    snapshot: object,
    context: RuntimeContext,
    coordinator: CompetitionCoordinator,
) -> list[dict[str, object]]:
    challenge_index = {
        challenge.code: challenge
        for challenge in getattr(snapshot, "challenges", [])
    }
    retired: list[dict[str, object]] = []
    for status in context.state_store.list_agent_statuses(role="challenge_worker"):
        if status.get("status") != "running":
            continue
        challenge_code = str(status.get("challenge_code") or "")
        challenge = challenge_index.get(challenge_code)
        if challenge is None:
            continue
        if not context.challenge_store.is_effectively_completed(challenge):
            continue
        metadata = dict(status.get("metadata") or {})
        metadata["retired_reason"] = "challenge already completed"
        await stop_challenge_instance_before_worker_exit(
            contest_gateway=context.contest_gateway,
            challenge_code=challenge_code,
            instance_status=getattr(challenge, "instance_status", None),
            event_logger=context.event_logger,
            reason="completed challenge retirement",
        )
        context.state_store.record_challenge_success(challenge_code)
        context.state_store.upsert_agent_status(
            agent_id=str(status["agent_id"]),
            role="challenge_worker",
            challenge_code=challenge_code,
            status="completed",
            summary="challenge completed; worker retired",
            metadata=metadata,
            last_error=str(status.get("last_error") or ""),
        )
        context.state_store.append_agent_event(
            agent_id=str(status["agent_id"]),
            challenge_code=challenge_code,
            event_type="worker_retired_completed_challenge",
            payload="worker cancelled because challenge is already completed",
        )
        await coordinator.cancel_worker(challenge_code)
        retired.append({"agent_id": str(status["agent_id"]), "challenge_code": challenge_code})
    return retired


async def run_competition_loop(context: RuntimeContext) -> None:
    histories: dict[str, list[dict[str, object]]] = {}
    findings_bus = ChallengeFindingsBus()
    coordinator = CompetitionCoordinator(max_parallel_challenges=3)
    competition_run_id = context.settings.competition_run_id or uuid4().hex[:8]
    manager_context = context.spawn(agent_id=build_manager_agent_id(competition_run_id), agent_role="manager")
    manager = CompetitionManagerAgent(manager_context, findings_bus)
    refresh_backoff = 1
    recovery_ran = False

    async def run_worker(challenge_code: str) -> None:
        worker_agent_id = build_worker_agent_id(challenge_code)
        worker_context = context.spawn(
            agent_id=worker_agent_id,
            agent_role="challenge_worker",
            challenge_code=challenge_code,
        )
        worker_context.state_store.delete_agent_statuses_for_challenge(
            challenge_code,
            role="challenge_worker",
            exclude_statuses={"completed"},
        )
        worker_context.state_store.append_agent_event(
            agent_id=worker_agent_id,
            challenge_code=challenge_code,
            event_type="worker_started",
            payload="worker run started",
        )
        backoff = context.settings.competition_error_backoff_seconds
        try:
            while True:
                agent_state = worker_context.state_store.get_agent_status(worker_agent_id)
                if agent_state is not None and agent_state.get("status") in {"pause_requested", "delete_requested"}:
                    command = str(agent_state["status"])
                    worker_context.state_store.clear_active_challenge(challenge_code)
                    await stop_challenge_instance_before_worker_exit(
                        contest_gateway=worker_context.contest_gateway,
                        challenge_code=challenge_code,
                        instance_status=None,
                        event_logger=worker_context.event_logger,
                        reason=f"{command} before worker exit",
                    )
                    worker_context.state_store.append_agent_event(
                        agent_id=worker_agent_id,
                        challenge_code=challenge_code,
                        event_type=command,
                        payload=f"worker acknowledged {command}",
                    )
                    if command == "delete_requested":
                        worker_context.state_store.delete_agent(worker_agent_id)
                    else:
                        worker_context.state_store.upsert_agent_status(
                            agent_id=worker_agent_id,
                            role="challenge_worker",
                            challenge_code=challenge_code,
                            status="paused",
                            summary="paused by operator",
                            metadata=dict(agent_state.get("metadata") or {}),
                            last_error=agent_state.get("last_error"),
                        )
                    return
                snapshot = await worker_context.challenge_store.refresh()
                target = next((item for item in snapshot.challenges if item.code == challenge_code), None)
                if target is None or target.completed:
                    await stop_challenge_instance_before_worker_exit(
                        contest_gateway=worker_context.contest_gateway,
                        challenge_code=challenge_code,
                        instance_status=getattr(target, "instance_status", None) if target is not None else None,
                        event_logger=worker_context.event_logger,
                        reason="completed challenge before worker exit",
                    )
                    worker_context.state_store.record_challenge_success(challenge_code)
                    worker_agent_id = worker_context.agent_id or worker_agent_id
                    worker_context.state_store.append_agent_event(
                        agent_id=worker_agent_id,
                        challenge_code=challenge_code,
                        event_type="worker_retired",
                        payload="challenge completed; worker retired from active execution",
                    )
                    worker_context.state_store.upsert_agent_status(
                        agent_id=worker_agent_id,
                        role="challenge_worker",
                        challenge_code=challenge_code,
                        status="completed",
                        summary="challenge completed",
                        metadata={
                            "challenge_code": challenge_code,
                            "retired": True,
                            "competition_run_id": competition_run_id,
                            "manager_agent_id": manager.agent_id,
                        },
                    )
                    return

                worker_context.notes["active_challenge"] = target.code
                target, instance_ready = await ensure_worker_target_instance_ready(
                    worker_context=worker_context,
                    target=target,
                    worker_agent_id=worker_agent_id,
                    competition_run_id=competition_run_id,
                    manager_agent_id=manager.agent_id,
                )
                if not instance_ready:
                    await asyncio.sleep(2)
                    continue
                worker_context.state_store.mark_active_challenge(target.code)
                runtime_state = worker_context.state_store.get_challenge_runtime_state(target.code)
                notes = compact_challenge_notes(worker_context.state_store.get_challenge_notes(target.code))
                if notes.get("operator_pause") == "true":
                    await stop_challenge_instance_before_worker_exit(
                        contest_gateway=worker_context.contest_gateway,
                        challenge_code=challenge_code,
                        instance_status=target.instance_status,
                        event_logger=worker_context.event_logger,
                        reason="operator pause before worker exit",
                    )
                    worker_context.state_store.append_agent_event(
                        agent_id=worker_agent_id,
                        challenge_code=challenge_code,
                        event_type="worker_paused",
                        payload="challenge paused by operator",
                    )
                    worker_context.state_store.upsert_agent_status(
                        agent_id=worker_agent_id,
                        role="challenge_worker",
                        challenge_code=challenge_code,
                        status="paused",
                        summary="paused by operator",
                        metadata={
                            "challenge_code": challenge_code,
                            "competition_run_id": competition_run_id,
                            "manager_agent_id": manager.agent_id,
                        },
                    )
                    worker_context.state_store.clear_active_challenge(target.code)
                    return
                seconds_in_attempt = worker_context.state_store.seconds_since_attempt_started(target.code)
                if (
                    seconds_in_attempt is not None
                    and seconds_in_attempt >= context.settings.competition_worker_max_seconds_per_challenge
                    and has_alternative_unfinished_challenges(
                        snapshot,
                        worker_context.state_store,
                        current_code=target.code,
                    )
                ):
                    reason = (
                        "long-running challenge attempt exceeded "
                        f"{context.settings.competition_worker_max_seconds_per_challenge} seconds; "
                        "temporarily yielding slot to an unstarted challenge"
                    )
                    worker_context.state_store.set_challenge_note(target.code, "deprioritized", "true")
                    worker_context.state_store.set_challenge_note(target.code, "deprioritized_reason", reason)
                    worker_context.state_store.add_history_event(target.code, "deferred", reason)
                    worker_context.state_store.add_challenge_memory(
                        target.code,
                        "deferred",
                        reason,
                        source=worker_context.agent_id or worker_agent_id,
                    )
                    worker_context.state_store.defer_challenge(
                        target.code,
                        defer_seconds=context.settings.competition_defer_seconds,
                        reason=reason,
                    )
                    await stop_challenge_instance_before_worker_exit(
                        contest_gateway=worker_context.contest_gateway,
                        challenge_code=target.code,
                        instance_status=target.instance_status,
                        event_logger=worker_context.event_logger,
                        reason="deferred challenge before worker exit",
                    )
                    worker_context.state_store.append_agent_event(
                        agent_id=worker_context.agent_id or worker_agent_id,
                        challenge_code=target.code,
                        event_type="worker_deferred",
                        payload=reason,
                    )
                    worker_context.state_store.upsert_agent_status(
                        agent_id=worker_context.agent_id or worker_agent_id,
                        role="challenge_worker",
                        challenge_code=target.code,
                        status="deferred",
                        summary="long-running challenge temporarily deferred",
                        metadata={
                            "challenge_code": target.code,
                            "competition_run_id": competition_run_id,
                            "manager_agent_id": manager.agent_id,
                            "defer_seconds": context.settings.competition_defer_seconds,
                        },
                    )
                    return
                seconds_since_progress = worker_context.state_store.seconds_since_progress(target.code)
                if should_view_hint(
                    int(runtime_state.get("failure_count", 0)),
                    target.hint_viewed,
                    notes,
                    seconds_since_progress=seconds_since_progress,
                    seconds_since_attempt=seconds_in_attempt,
                ):
                    hint_payload = await worker_context.contest_gateway.view_hint(target.code)
                    worker_context.state_store.add_history_event(target.code, "hint_viewed", str(hint_payload))
                    worker_context.state_store.set_challenge_note(target.code, "hint_viewed", "true")
                    worker_context.state_store.add_challenge_memory(
                        target.code,
                        "hint_viewed",
                        str(hint_payload),
                        source=worker_context.agent_id or worker_agent_id,
                    )
                    notes = compact_challenge_notes(worker_context.state_store.get_challenge_notes(target.code))

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
                    notes = compact_challenge_notes(worker_context.state_store.get_challenge_notes(target.code))
                available_skills = worker_context.skill_registry.describe_available() if worker_context.skill_registry else None
                worker_context.state_store.upsert_agent_status(
                    agent_id=worker_context.agent_id or worker_agent_id,
                    role="challenge_worker",
                    challenge_code=target.code,
                    status="running",
                    summary=f"{target.title} / {skill_plan.stage if skill_plan else 'recon'}",
                    metadata={
                        "track": infer_track(target.description),
                        "stage": skill_plan.stage if skill_plan else "recon",
                        "instance_status": target.instance_status,
                        "competition_run_id": competition_run_id,
                        "manager_agent_id": manager.agent_id,
                        "model_routing": (
                            worker_context.provider_router.describe()
                            if worker_context.provider_router is not None
                            else None
                        ),
                    },
                )
                client = worker_context.provider_router.build_client() if worker_context.provider_router is not None else None
                if client is None:
                    raise RuntimeError("model provider router unavailable")

                agent = AsyncPentestAgent(
                    client=client,
                    model_name=context.settings.model,
                    system_prompt="\n\n".join(
                        [
                            build_entry_prompt(
                                "competition",
                                None,
                                None,
                                [],
                                available_skills=available_skills,
                                operator_resources={
                                    "callback_server": worker_context.settings.callback_resource,
                                }
                                if worker_context.settings.callback_resource
                                else None,
                            ),
                            build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                            build_trigger_prompt(PRE_EXPLOIT_PROMPT),
                            build_trigger_prompt(RECOVERY_PROMPT) if int(runtime_state.get("failure_count", 0)) > 0 else "",
                            build_trigger_prompt(HINT_DECISION_PROMPT) if notes.get("hint_viewed") == "true" else "",
                            build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                        ]
                    ),
                    tool_bus=ToolBus(worker_context),
                    workdir=worker_context.settings.runtime_dir,
                    context_window_tokens=worker_context.settings.model_context_window_tokens,
                    context_compaction_threshold_ratio=worker_context.settings.context_compaction_threshold_ratio,
                    estimated_chars_per_token=worker_context.settings.estimated_chars_per_token,
                    context_compaction_keep_tail_messages=worker_context.settings.context_compaction_keep_tail_messages,
                    context_compaction_keep_recent_tool_results=worker_context.settings.context_compaction_keep_recent_tool_results,
                    context_compaction_tool_result_preview_chars=worker_context.settings.context_compaction_tool_result_preview_chars,
                    context_compaction_summary_input_chars=worker_context.settings.context_compaction_summary_input_chars,
                    context_compaction_summary_max_tokens=worker_context.settings.context_compaction_summary_max_tokens,
                )
                prompt = worker_context.challenge_store.build_autonomous_prompt(
                    snapshot,
                    target,
                    stage=skill_plan.stage if skill_plan else None,
                    runtime_state=runtime_state,
                    notes=notes,
                    track=infer_track(target.description),
                    selected_skills=skill_plan.skills if skill_plan else [],
                    available_skills=available_skills,
                    operator_resources={
                        "callback_server": worker_context.settings.callback_resource,
                    }
                    if worker_context.settings.callback_resource
                    else None,
                )
                result = await agent.execute(prompt, histories.get(target.code))
                histories[target.code] = result.history
                worker_context.state_store.add_history_event(target.code, "turn_completed", result.output or "")
                if result.output or result.tool_events:
                    worker_context.state_store.mark_progress(target.code)
                if result.output:
                    worker_context.state_store.add_challenge_memory(
                        target.code,
                        "turn_summary",
                        result.output[:2000],
                        source=worker_context.agent_id or worker_agent_id,
                    )
                extracted_notes = extract_runtime_notes(
                    result.output,
                    [{"name": event.name, "arguments": event.arguments, "output": event.output} for event in result.tool_events],
                )
                for key, value in extracted_notes.items():
                    worker_context.state_store.set_challenge_note(target.code, key, value)
                    worker_context.state_store.add_challenge_memory(
                        target.code,
                        key,
                        value,
                        source=worker_context.agent_id or worker_agent_id,
                    )
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
                worker_context.state_store.record_challenge_turn_success(target.code)
                worker_context.state_store.append_agent_event(
                    agent_id=worker_context.agent_id or worker_agent_id,
                    challenge_code=target.code,
                    event_type="worker_turn_completed",
                    payload=(result.output or "")[:1000],
                )
                backoff = context.settings.competition_error_backoff_seconds
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            worker_context.state_store.clear_active_challenge(challenge_code)
            existing_status = worker_context.state_store.get_agent_status(worker_context.agent_id or worker_agent_id)
            if existing_status is not None and existing_status.get("status") == "waiting_recovery":
                worker_context.state_store.append_agent_event(
                    agent_id=worker_context.agent_id or worker_agent_id,
                    challenge_code=challenge_code,
                    event_type="worker_cancelled_for_recovery",
                    payload="worker cancelled after stall detection",
                )
                raise
            worker_context.state_store.upsert_agent_status(
                agent_id=worker_context.agent_id or worker_agent_id,
                role="challenge_worker",
                challenge_code=challenge_code,
                status="cancelled",
                summary="worker cancelled",
                metadata={
                    "challenge_code": challenge_code,
                    "competition_run_id": competition_run_id,
                    "manager_agent_id": manager.agent_id,
                },
            )
            raise
        except Exception as exc:  # pragma: no cover - runtime recovery path
            worker_context.notes["last_error"] = str(exc)
            failure_count = worker_context.state_store.record_challenge_failure(challenge_code, str(exc))
            worker_context.state_store.add_history_event(challenge_code, "error", str(exc))
            worker_context.state_store.set_challenge_note(challenge_code, "last_error", str(exc))
            worker_context.state_store.add_challenge_memory(
                challenge_code,
                "error",
                str(exc),
                source=worker_context.agent_id or worker_agent_id,
            )
            worker_context.state_store.upsert_agent_status(
                agent_id=worker_context.agent_id or worker_agent_id,
                role="challenge_worker",
                challenge_code=challenge_code,
                status="error",
                summary="worker failed; waiting for recovery",
                metadata={
                    "challenge_code": challenge_code,
                    "competition_run_id": competition_run_id,
                    "manager_agent_id": manager.agent_id,
                },
                last_error=str(exc),
            )
            worker_context.state_store.append_agent_event(
                agent_id=worker_context.agent_id or worker_agent_id,
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
                context.event_logger.log(
                    "competition.refresh_error",
                    {
                        "error": "challenge refresh raised CancelledError; retrying",
                        "backoff_seconds": refresh_backoff,
                    },
                )
                manager_context.state_store.upsert_agent_status(
                    agent_id=manager.agent_id,
                    role="manager",
                    challenge_code=None,
                    status="degraded",
                    summary="challenge refresh cancelled; retrying",
                    metadata={"backoff_seconds": refresh_backoff, "run_id": competition_run_id},
                    last_error="challenge refresh raised CancelledError",
                )
                await asyncio.sleep(refresh_backoff)
                refresh_backoff = min(refresh_backoff * 2, context.settings.competition_max_error_backoff_seconds)
                continue
            except Exception as exc:  # pragma: no cover - runtime recovery path
                context.event_logger.log(
                    "competition.refresh_error",
                    {
                        "error": str(exc),
                        "backoff_seconds": refresh_backoff,
                    },
                )
                manager_context.state_store.upsert_agent_status(
                    agent_id=manager.agent_id,
                    role="manager",
                    challenge_code=None,
                    status="degraded",
                    summary="challenge refresh failed; retrying",
                    metadata={"backoff_seconds": refresh_backoff, "run_id": competition_run_id},
                    last_error=str(exc),
                )
                await asyncio.sleep(refresh_backoff)
                refresh_backoff = min(refresh_backoff * 2, context.settings.competition_max_error_backoff_seconds)
                continue
            if not recovery_ran:
                recovery_summary = recover_competition_state(
                    snapshot=snapshot,
                    state_store=context.state_store,
                    competition_run_id=competition_run_id,
                )
                context.event_logger.log("competition.recovery", recovery_summary)
                recovery_ran = True
            closed_instances = await close_completed_challenge_instances(
                snapshot=snapshot,
                context=context,
            )
            if closed_instances:
                context.event_logger.log(
                    "competition.completed_instances_closed",
                    {"challenge_codes": closed_instances},
                )
            orphaned_instances = await close_orphaned_challenge_instances(
                snapshot=snapshot,
                context=context,
                coordinator=coordinator,
            )
            if orphaned_instances:
                context.event_logger.log(
                    "competition.orphaned_instances_closed",
                    {"challenge_codes": orphaned_instances},
                )
            recovered_workers = await recover_stalled_workers(
                snapshot=snapshot,
                context=context,
                coordinator=coordinator,
                stall_seconds=context.settings.competition_worker_stall_seconds,
            )
            if recovered_workers:
                context.event_logger.log(
                    "competition.stalled_workers_recovered",
                    {"recovered_workers": recovered_workers},
                )
            retired_workers = await retire_completed_workers(
                snapshot=snapshot,
                context=context,
                coordinator=coordinator,
            )
            if retired_workers:
                context.event_logger.log(
                    "competition.completed_workers_retired",
                    {"retired_workers": retired_workers},
                )
            manager.heartbeat(snapshot, coordinator)
            manager.reconcile(coordinator)
            candidates, _paused = partition_dispatchable_challenges(
                snapshot,
                context.state_store,
                fill_idle_workers=True,
            )

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
