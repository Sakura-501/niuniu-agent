from __future__ import annotations

import asyncio
import contextlib
import html
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from typing import AsyncIterator
from uuid import uuid4

from niuniu_agent.agent_stack.agent import AsyncPentestAgent
from niuniu_agent.agent_stack.prompts import (
    CHALLENGE_TAKEOVER_PROMPT,
    FLAG_SUBMIT_PROMPT,
    build_entry_prompt,
    build_trigger_prompt,
)
from niuniu_agent.agent_stack.tool_bus import ToolBus
from niuniu_agent.config import AgentSettings
from niuniu_agent.control_plane import ChallengeStore, ContestGateway
from niuniu_agent.model_routing import ModelProviderRouter
from niuniu_agent.runtime.answer_formatter import should_format_debug_answer, stream_formatted_answer
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.skills import SkillRegistry
from niuniu_agent.skills.planner import plan_skills
from niuniu_agent.skills.tracks import infer_track
from niuniu_agent.state_store import StateStore
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox


class CompetitionProcessController:
    def __init__(self, repo_root: Path, runtime_dir: Path, web_port: int) -> None:
        self.repo_root = repo_root
        self.runtime_dir = runtime_dir
        self.web_port = web_port
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.competition_pid_file = self.runtime_dir / "competition.pid"
        self.competition_log_file = self.runtime_dir / "competition.log"
        self.competition_run_id_file = self.runtime_dir / "competition.run_id"

    def status(self) -> dict[str, object]:
        pid = self._read_pid(self.competition_pid_file)
        return {
            "competition": {
                "running": self._pid_running(pid),
                "pid": pid,
                "log_path": str(self.competition_log_file),
                "runtime_dir": str(self.runtime_dir),
                "run_id": self._read_run_id(),
            },
            "ui": {
                "running": True,
                "pid": os.getpid(),
                "port": self.web_port,
                "runtime_dir": str(self.runtime_dir),
            },
        }

    async def start_competition(self) -> dict[str, object]:
        pid = self._read_pid(self.competition_pid_file)
        if self._pid_running(pid):
            return {"ok": True, "already_running": True, "pid": pid, "run_id": self._read_run_id()}
        run_id = uuid4().hex[:8]
        self.competition_log_file.parent.mkdir(parents=True, exist_ok=True)
        command = self._build_competition_command(prefer_uv=shutil.which("uv") is not None)
        with self.competition_log_file.open("a", encoding="utf-8") as handle:
            process = subprocess.Popen(
                command,
                cwd=self.repo_root,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={
                    **os.environ.copy(),
                    "NIUNIU_AGENT_RUNTIME_DIR": str(self.runtime_dir),
                    "NIUNIU_AGENT_COMPETITION_RUN_ID": run_id,
                },
            )
        self.competition_pid_file.write_text(str(process.pid), encoding="utf-8")
        self.competition_run_id_file.write_text(run_id, encoding="utf-8")
        return {"ok": True, "pid": process.pid, "run_id": run_id}

    @staticmethod
    def _build_competition_command(*, prefer_uv: bool) -> list[str]:
        if prefer_uv:
            return ["uv", "run", "niuniu-agent", "run", "--mode", "competition"]
        return ["python", "-m", "niuniu_agent.cli", "run", "--mode", "competition"]

    async def stop_competition(self) -> dict[str, object]:
        pid = self._read_pid(self.competition_pid_file)
        if not self._pid_running(pid):
            self.competition_pid_file.unlink(missing_ok=True)
            self.competition_run_id_file.unlink(missing_ok=True)
            return {"ok": True, "already_stopped": True}
        assert pid is not None
        os.kill(pid, signal.SIGTERM)
        self.competition_pid_file.unlink(missing_ok=True)
        self.competition_run_id_file.unlink(missing_ok=True)
        return {"ok": True, "pid": pid}

    async def restart_competition(self) -> dict[str, object]:
        await self.stop_competition()
        return await self.start_competition()

    @staticmethod
    def _read_pid(path: Path) -> int | None:
        if not path.exists():
            return None
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except ValueError:
            return None

    def _read_run_id(self) -> str | None:
        if not self.competition_run_id_file.exists():
            return None
        value = self.competition_run_id_file.read_text(encoding="utf-8").strip()
        return value or None

    @staticmethod
    def _pid_running(pid: int | None) -> bool:
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True


class DebugSessionManager:
    def __init__(self, base_context: RuntimeContext) -> None:
        self.base_context = base_context
        self._histories: dict[str, list[dict[str, object]]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._partial_outputs: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> str:
        session_id = uuid4().hex[:12]
        async with self._lock:
            self._histories[session_id] = []
        self.base_context.state_store.upsert_agent_status(
            agent_id=f"debug:{session_id}",
            role="debug",
            challenge_code=None,
            status="idle",
            summary="session created",
            metadata={"session_id": session_id},
        )
        return session_id

    async def get_session(self, session_id: str) -> dict[str, object]:
        agent_id = f"debug:{session_id}"
        async with self._lock:
            task = self._tasks.get(session_id)
            partial_output = self._partial_outputs.get(session_id, "")
            if task is not None and task.done():
                self._tasks.pop(session_id, None)
        status = self.base_context.state_store.get_agent_status(agent_id)
        transcript: list[dict[str, object]] = []
        for event in self.base_context.state_store.list_agent_events(
            agent_id=agent_id,
            limit=400,
            ascending=True,
        ):
            if event["event_type"] == "debug_user_message":
                transcript.append({"role": "user", "text": event["payload"], "created_at": event["created_at"]})
            elif event["event_type"] == "debug_assistant_message":
                transcript.append({"role": "assistant", "text": event["payload"], "created_at": event["created_at"]})
            elif event["event_type"] in {"tool_start", "tool_done", "tool_error"}:
                transcript.append(
                    {
                        "role": "tool",
                        "event_type": event["event_type"],
                        "text": event["payload"],
                        "created_at": event["created_at"],
                    }
                )
        return {
            "session_id": session_id,
            "agent_id": agent_id,
            "status": status["status"] if status is not None else "missing",
            "agent_status": status,
            "partial_output": partial_output,
            "transcript": transcript,
            "actions": ["stop", "delete"],
        }

    async def stop_session(self, session_id: str) -> dict[str, object]:
        agent_id = f"debug:{session_id}"
        async with self._lock:
            task = self._tasks.get(session_id)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self.base_context.state_store.upsert_agent_status(
            agent_id=agent_id,
            role="debug",
            challenge_code=None,
            status="cancelled",
            summary="session stopped by operator",
            metadata={"session_id": session_id},
        )
        self.base_context.state_store.append_agent_event(
            agent_id=agent_id,
            challenge_code=None,
            event_type="debug_session_stopped",
            payload="stopped by operator",
        )
        async with self._lock:
            self._tasks.pop(session_id, None)
            self._partial_outputs.pop(session_id, None)
        return {"ok": True, "agent_id": agent_id, "action": "stop"}

    async def delete_session(self, session_id: str) -> dict[str, object]:
        agent_id = f"debug:{session_id}"
        await self.stop_session(session_id)
        async with self._lock:
            self._histories.pop(session_id, None)
            self._tasks.pop(session_id, None)
            self._partial_outputs.pop(session_id, None)
        self.base_context.state_store.delete_agent(agent_id)
        return {"ok": True, "agent_id": agent_id, "action": "delete"}

    async def stream_reply(self, session_id: str, user_input: str) -> AsyncIterator[str]:
        async with self._lock:
            history = list(self._histories.setdefault(session_id, []))
            running = self._tasks.get(session_id)
        if running is not None and not running.done():
            yield self._sse("error", {"message": "session already running"})
            return

        snapshot = await self.base_context.challenge_store.refresh()
        active = self.base_context.challenge_store.next_candidate(snapshot)
        turn_context = self.base_context.spawn(
            agent_id=f"debug:{session_id}",
            agent_role="debug",
            challenge_code=active.code if active is not None else None,
        )
        turn_context.notes["latest_snapshot"] = self.base_context.challenge_store.export_json(snapshot)
        runtime_state = (
            turn_context.state_store.get_challenge_runtime_state(active.code)
            if active is not None
            else {}
        )
        notes = turn_context.state_store.get_challenge_notes(active.code) if active is not None else {}
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
                        snapshot,
                        active,
                        skill_plan.skills if skill_plan else [],
                        available_skills=available_skills,
                        stage=skill_plan.stage if skill_plan else None,
                        runtime_state=runtime_state,
                        notes=notes,
                        summary_request=False,
                        track=track,
                    ),
                    build_trigger_prompt(CHALLENGE_TAKEOVER_PROMPT),
                    build_trigger_prompt(FLAG_SUBMIT_PROMPT),
                ]
            ),
            tool_bus=ToolBus(turn_context),
        )
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        buffered_text_chunks: list[str] = []

        async def on_text_delta(text: str) -> None:
            buffered_text_chunks.append(text)
            async with self._lock:
                self._partial_outputs[session_id] = self._partial_outputs.get(session_id, "") + text
            await queue.put(self._sse("model", {"text": text}))

        async def on_tool_start(name: str, arguments: dict[str, object]) -> None:
            await queue.put(self._sse("tool_start", {"name": name, "arguments": arguments}))

        async def on_tool_end(name: str, arguments: dict[str, object], output: str) -> None:
            await queue.put(
                self._sse(
                    "tool_done",
                    {"name": name, "arguments": arguments, "output_preview": output[:500]},
                )
            )

        async def run() -> None:
            try:
                turn_context.state_store.append_agent_event(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    challenge_code=turn_context.challenge_code,
                    event_type="debug_user_message",
                    payload=user_input,
                )
                turn_context.state_store.upsert_agent_status(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    role="debug",
                    challenge_code=turn_context.challenge_code,
                    status="running",
                    summary=user_input[:240],
                    metadata={"session_id": session_id},
                )
                result = await agent.execute_stream(
                    user_input,
                    history,
                    on_text_delta=on_text_delta,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                )
                raw_output = result.output or "".join(buffered_text_chunks)
                final_output = raw_output
                if should_format_debug_answer(user_input, result.tool_events):
                    formatted_chunks: list[str] = []

                    async def on_final_delta(text: str) -> None:
                        formatted_chunks.append(text)
                        await queue.put(self._sse("final", {"text": text}))

                    formatted = await stream_formatted_answer(
                        client=client,
                        model_name=turn_context.settings.model,
                        user_input=user_input,
                        raw_output=raw_output,
                        tool_events=result.tool_events,
                        on_text_delta=on_final_delta,
                    )
                    final_output = formatted or "".join(formatted_chunks) or raw_output
                async with self._lock:
                    self._histories[session_id] = result.history
                    self._partial_outputs.pop(session_id, None)
                turn_context.state_store.upsert_agent_status(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    role="debug",
                    challenge_code=turn_context.challenge_code,
                    status="idle",
                    summary=(final_output or user_input)[:240],
                    metadata={"session_id": session_id},
                )
                turn_context.state_store.append_agent_event(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    challenge_code=turn_context.challenge_code,
                    event_type="debug_assistant_message",
                    payload=final_output[:4000] if final_output else "",
                )
                turn_context.state_store.append_agent_event(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    challenge_code=turn_context.challenge_code,
                    event_type="debug_turn_completed",
                    payload=final_output[:1000] if final_output else user_input,
                )
                await queue.put(self._sse("done", {"text": final_output}))
            except Exception as exc:  # noqa: BLE001
                turn_context.state_store.upsert_agent_status(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    role="debug",
                    challenge_code=turn_context.challenge_code,
                    status="error",
                    summary="debug turn failed",
                    metadata={"session_id": session_id},
                    last_error=str(exc),
                )
                turn_context.state_store.append_agent_event(
                    agent_id=turn_context.agent_id or f"debug:{session_id}",
                    challenge_code=turn_context.challenge_code,
                    event_type="debug_turn_error",
                    payload=str(exc),
                )
                async with self._lock:
                    self._partial_outputs.pop(session_id, None)
                await queue.put(self._sse("error", {"message": str(exc)}))
            finally:
                async with self._lock:
                    self._tasks.pop(session_id, None)
                await queue.put(None)

        task = asyncio.create_task(run())
        async with self._lock:
            self._tasks[session_id] = task
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            await task

    @staticmethod
    def _sse(event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class AgentWebService:
    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.settings: AgentSettings | None = None
        self.context: RuntimeContext | None = None
        self.contest_gateway: ContestGateway | None = None
        self.controller: CompetitionProcessController | None = None
        self.debug_sessions: DebugSessionManager | None = None

    async def startup(self) -> None:
        self.settings = AgentSettings()
        event_logger = EventLogger(self.settings.runtime_dir / "events.jsonl")
        state_store = StateStore(self.settings.runtime_dir / "state.db")
        local_toolbox = LocalToolbox(self.settings.runtime_dir)
        skill_registry = SkillRegistry()
        provider_router = ModelProviderRouter(self.settings, state_store)
        self.contest_gateway = ContestGateway.from_settings(self.settings)
        await self.contest_gateway.connect()
        challenge_store = ChallengeStore(contest_client=self.contest_gateway, state_store=state_store)
        self.context = RuntimeContext(
            settings=self.settings,
            contest_gateway=self.contest_gateway,
            challenge_store=challenge_store,
            state_store=state_store,
            event_logger=event_logger,
            local_toolbox=local_toolbox,
            skill_registry=skill_registry,
            provider_router=provider_router,
        )
        self.controller = CompetitionProcessController(
            repo_root=self.repo_root,
            runtime_dir=self.settings.runtime_dir,
            web_port=self.settings.web_port,
        )
        self.debug_sessions = DebugSessionManager(self.context)

    async def shutdown(self) -> None:
        if self.contest_gateway is not None:
            await self.contest_gateway.cleanup()

    async def overview(self) -> dict[str, object]:
        assert self.context is not None and self.controller is not None
        snapshot = await self.context.challenge_store.refresh()
        stored_agents = self.context.state_store.list_agent_statuses()
        process_status = self.controller.status()
        contest = self.context.challenge_store.export_json(snapshot)
        for challenge in contest["challenges"]:
            agent_statuses = self.context.state_store.list_agent_statuses(challenge_code=challenge["code"])
            challenge.update(build_challenge_scheduler_view(challenge, agent_statuses))
        return {
            "listening_port": self.context.settings.web_port,
            "process": process_status,
            "model_routing": self.context.provider_router.describe() if self.context.provider_router is not None else {},
            "contest_capabilities": [
                "list_challenges",
                "start_challenge",
                "stop_challenge",
                "submit_flag",
                "view_hint",
            ],
            "data_sources": {
                "official": "contest MCP list_challenges/start_challenge/stop_challenge/submit_flag/view_hint",
                "local": "state.db: runtime_state + notes + history + agent_status + agent_events",
            },
            "contest": contest,
            "agents": build_agent_overview_rows(stored_agents, process_status, max_parallel_workers=3),
            "agent_tree": build_agent_tree(stored_agents, process_status, max_parallel_workers=3),
            "recent_agent_events": self.context.state_store.list_agent_events(limit=80),
        }

    async def get_model_routing(self) -> dict[str, object]:
        assert self.context is not None and self.context.provider_router is not None
        return self.context.provider_router.describe()

    async def select_model_routing(self, provider_id: str, model_override: str | None) -> dict[str, object]:
        assert self.context is not None and self.context.provider_router is not None
        return self.context.provider_router.set_selection(provider_id, model_override)

    async def reset_model_routing(self) -> dict[str, object]:
        assert self.context is not None and self.context.provider_router is not None
        return self.context.provider_router.clear_selection()

    async def challenge_detail(self, code: str) -> dict[str, object]:
        assert self.context is not None
        snapshot = await self.context.challenge_store.refresh()
        exported = self.context.challenge_store.export_json(snapshot)
        local = {
            "runtime_state": self.context.state_store.get_challenge_runtime_state(code),
            "submitted_flags": self.context.state_store.list_submitted_flags(code),
            "notes": self.context.state_store.get_challenge_notes(code),
            "memories": self.context.state_store.list_challenge_memories(code, limit=50),
            "history": self.context.state_store.list_history(code, limit=50),
            "agent_statuses": self.context.state_store.list_agent_statuses(challenge_code=code),
            "events": self.context.state_store.list_agent_events(challenge_code=code, limit=200, ascending=True),
        }
        challenge = next((item for item in exported["challenges"] if item["code"] == code), None)
        if challenge is None:
            availability = "local-only" if any(local.values()) else "missing"
            return {
                "code": code,
                "availability": availability,
                "official": None,
                "local": local,
                "source_summary": {
                    "official": "contest MCP list_challenges",
                    "local": "state.db persisted runtime/history/notes/memories",
                },
            }
        official = {
            key: value
            for key, value in challenge.items()
            if key
            not in {"locally_submitted_flags", "runtime_state", "notes", "recent_history", "recent_memories"}
        }
        return {
            "code": code,
            "availability": "official+local",
            "official": {
                **official,
                **build_challenge_scheduler_view(challenge, local["agent_statuses"]),
            },
            "local": local,
            "source_summary": {
                "official": "contest MCP list_challenges",
                "local": "state.db persisted runtime/history/notes/memories",
            },
        }

    async def agent_detail(self, agent_id: str) -> dict[str, object]:
        assert self.context is not None
        status = self.context.state_store.get_agent_status(agent_id)
        actions: list[str] = []
        if agent_id.startswith("debug:"):
            actions = ["stop", "delete"]
        elif status is not None and status.get("role") == "manager":
            actions = ["stop", "delete"]
        elif status is not None and status.get("role") == "challenge_worker":
            if status.get("status") not in {"completed", "cancelled", "paused"}:
                actions.append("pause")
            actions.append("delete")
        return {
            "agent_id": agent_id,
            "status": status,
            "events": self.context.state_store.list_agent_events(agent_id=agent_id, limit=200, ascending=True),
            "actions": actions,
        }

    async def create_debug_session(self) -> dict[str, object]:
        assert self.debug_sessions is not None
        return {"session_id": await self.debug_sessions.create_session()}

    async def get_debug_session(self, session_id: str) -> dict[str, object]:
        assert self.debug_sessions is not None
        return await self.debug_sessions.get_session(session_id)

    async def stream_debug_reply(self, session_id: str, message: str) -> AsyncIterator[str]:
        assert self.debug_sessions is not None
        async for chunk in self.debug_sessions.stream_reply(session_id, message):
            yield chunk

    async def stop_agent(self, agent_id: str) -> dict[str, object]:
        if agent_id.startswith("debug:") and self.debug_sessions is not None:
            return await self.debug_sessions.stop_session(agent_id.removeprefix("debug:"))
        if agent_id.startswith("manager:competition"):
            process_state = self.controller.status()["competition"] if self.controller is not None else {}
            run_id = self._manager_run_id(agent_id)
            current_run_id = process_state.get("run_id")
            should_stop = False
            if process_state.get("running"):
                if run_id is None:
                    should_stop = True
                elif current_run_id == run_id:
                    should_stop = True
            if should_stop and self.controller is not None:
                await self.controller.stop_competition()
            return {"ok": True, "agent_id": agent_id, "action": "stop"}
        return {"ok": False, "agent_id": agent_id, "action": "stop", "reason": "unsupported"}

    async def pause_agent(self, agent_id: str) -> dict[str, object]:
        assert self.context is not None
        status = self.context.state_store.get_agent_status(agent_id)
        if status is None:
            return {"ok": False, "agent_id": agent_id, "action": "pause", "reason": "missing"}
        if status.get("role") != "challenge_worker":
            return {"ok": False, "agent_id": agent_id, "action": "pause", "reason": "unsupported"}
        challenge_code = status.get("challenge_code")
        if challenge_code:
            self.context.state_store.set_challenge_note(str(challenge_code), "operator_pause", "true")
        self.context.state_store.upsert_agent_status(
            agent_id=agent_id,
            role="challenge_worker",
            challenge_code=str(challenge_code) if challenge_code else None,
            status="pause_requested",
            summary="pause requested by operator",
            metadata=dict(status.get("metadata") or {}),
            last_error=status.get("last_error"),
        )
        self.context.state_store.append_agent_event(
            agent_id=agent_id,
            challenge_code=str(challenge_code) if challenge_code else None,
            event_type="pause_requested",
            payload="pause requested by operator",
        )
        return {"ok": True, "agent_id": agent_id, "action": "pause"}

    async def delete_agent(self, agent_id: str) -> dict[str, object]:
        assert self.context is not None
        if agent_id.startswith("debug:") and self.debug_sessions is not None:
            return await self.debug_sessions.delete_session(agent_id.removeprefix("debug:"))
        if agent_id.startswith("manager:competition"):
            process_state = self.controller.status()["competition"] if self.controller is not None else {}
            run_id = self._manager_run_id(agent_id)
            current_run_id = process_state.get("run_id")
            should_stop = False
            if process_state.get("running"):
                if run_id is None:
                    should_stop = True
                elif current_run_id == run_id:
                    should_stop = True
            if should_stop and self.controller is not None:
                await self.controller.stop_competition()
            if run_id is not None:
                self._delete_competition_run(run_id)
            else:
                self.context.state_store.delete_agent(agent_id)
            return {"ok": True, "agent_id": agent_id, "action": "delete"}
        status = self.context.state_store.get_agent_status(agent_id)
        if status is None:
            self.context.state_store.delete_agent(agent_id)
            return {"ok": True, "agent_id": agent_id, "action": "delete"}
        if status.get("role") == "challenge_worker":
            challenge_code = status.get("challenge_code")
            if challenge_code and status.get("status") not in {"completed", "cancelled", "paused"}:
                self.context.state_store.upsert_agent_status(
                    agent_id=agent_id,
                    role="challenge_worker",
                    challenge_code=str(challenge_code),
                    status="delete_requested",
                    summary="delete requested by operator",
                    metadata=dict(status.get("metadata") or {}),
                    last_error=status.get("last_error"),
                )
                self.context.state_store.append_agent_event(
                    agent_id=agent_id,
                    challenge_code=str(challenge_code),
                    event_type="delete_requested",
                    payload="delete requested by operator",
                )
                return {"ok": True, "agent_id": agent_id, "action": "delete"}
            self.context.state_store.delete_agent(agent_id)
            return {"ok": True, "agent_id": agent_id, "action": "delete"}
        return {"ok": False, "agent_id": agent_id, "action": "delete", "reason": "unsupported"}

    def _delete_competition_run(self, run_id: str) -> None:
        assert self.context is not None
        for agent in self.context.state_store.list_agent_statuses():
            metadata = agent.get("metadata") or {}
            if agent["agent_id"] == f"manager:competition:{run_id}" or metadata.get("competition_run_id") == run_id:
                self.context.state_store.delete_agent(str(agent["agent_id"]))

    @staticmethod
    def _manager_run_id(agent_id: str) -> str | None:
        parts = agent_id.split(":")
        if len(parts) >= 3:
            return parts[-1]
        return None

    async def start_competition(self) -> dict[str, object]:
        assert self.controller is not None and self.context is not None
        result = await self.controller.start_competition()
        manager_agent_id = f"manager:competition:{result.get('run_id') or 'pending'}"
        self.context.state_store.upsert_agent_status(
            agent_id=manager_agent_id,
            role="manager",
            challenge_code=None,
            status="starting",
            summary="competition process starting",
            metadata={"source": "web-ui", "runtime_dir": str(self.context.settings.runtime_dir), "run_id": result.get("run_id")},
        )
        self.context.state_store.append_agent_event(
            agent_id=manager_agent_id,
            challenge_code=None,
            event_type="competition_start_requested",
            payload="requested from web ui",
        )
        result["agents_seeded"] = [
            self.context.state_store.get_agent_status(manager_agent_id),
        ]
        return result

    async def stop_competition(self) -> dict[str, object]:
        assert self.controller is not None
        return await self.controller.stop_competition()

    async def restart_competition(self) -> dict[str, object]:
        assert self.controller is not None
        return await self.controller.restart_competition()


def page_shell(title: str, body: str, script: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    :root {{
      --bg: #f6f4ef;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d9d4c7;
      --accent: #0f766e;
      --accent-soft: #ccfbf1;
      --warn: #9a3412;
      --warn-soft: #ffedd5;
      --shadow: 0 24px 48px rgba(31, 41, 55, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.10), transparent 32%),
        linear-gradient(180deg, #fbfaf6 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: 'IBM Plex Sans', sans-serif;
    }}
    a {{ color: inherit; }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid rgba(217,212,199,0.8);
      position: sticky;
      top: 0;
      backdrop-filter: blur(14px);
      background: rgba(251,250,246,0.88);
    }}
    .brand {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}
    .brand h1 {{
      margin: 0;
      font-size: 28px;
      letter-spacing: -0.03em;
    }}
    .brand p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
    }}
    nav {{
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}
    nav a {{
      padding: 10px 14px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 999px;
      text-decoration: none;
      box-shadow: var(--shadow);
    }}
    main {{
      padding: 28px 32px 40px;
    }}
    .layout {{
      display: grid;
      gap: 18px;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 18px 18px 16px;
      box-shadow: var(--shadow);
    }}
    .panel h2, .panel h3 {{
      margin: 0 0 12px;
      font-size: 18px;
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
      margin-bottom: 10px;
    }}
    .button-row {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    button {{
      appearance: none;
      border: 0;
      cursor: pointer;
      border-radius: 14px;
      padding: 11px 14px;
      font-family: inherit;
      font-weight: 600;
      background: var(--ink);
      color: #fff;
    }}
    button.secondary {{
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .card-list {{
      display: grid;
      gap: 12px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.68);
    }}
    .muted {{ color: var(--muted); }}
    .mono, pre, code {{
      font-family: 'IBM Plex Mono', monospace;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #172033;
      color: #e2f7f3;
      border-radius: 16px;
      padding: 14px;
      overflow: auto;
    }}
    textarea {{
      width: 100%;
      min-height: 120px;
      border-radius: 18px;
      border: 1px solid var(--line);
      padding: 14px;
      font: inherit;
      background: #fff;
    }}
    .chat-log {{
      min-height: 260px;
      max-height: 540px;
      overflow: auto;
      display: grid;
      gap: 10px;
    }}
    .bubble {{
      border-radius: 18px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .bubble.user {{
      background: var(--warn-soft);
      border-color: #fdba74;
    }}
    .bubble.tool {{
      background: #f0fdfa;
      border-color: #99f6e4;
    }}
    @media (max-width: 960px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .grid-2 {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div>
        <h1>{html.escape(title)}</h1>
        <p>niuniu-agent Web Console · 默认监听 8081 · 实时查看 manager / worker / debug agent 状态</p>
      </div>
      <div class="eyebrow mono">port 8081</div>
    </div>
    <nav>
      <a href="/">Dashboard</a>
      <a href="/debug">Debug Chat</a>
    </nav>
  </header>
  <main>
    {body}
  </main>
  <script>{script}</script>
</body>
</html>"""


def build_agent_overview_rows(
    stored_agents: list[dict[str, object]],
    process_status: dict[str, object],
    *,
    max_parallel_workers: int,
) -> list[dict[str, object]]:
    rows = list(stored_agents)
    by_id = {str(item["agent_id"]): item for item in rows}
    competition_state = dict(process_status.get("competition") or {})
    effective_run_id = competition_state.get("run_id") or _infer_competition_run_id(rows)
    if competition_state.get("running"):
        manager_agent_id = f"manager:competition:{effective_run_id or 'current'}"
        if manager_agent_id not in by_id:
            rows.insert(
                0,
                {
                    "agent_id": manager_agent_id,
                    "role": "manager",
                    "challenge_code": None,
                    "status": "starting",
                    "summary": "competition process is running but manager status has not been persisted yet",
                    "metadata": {"synthetic": True, "run_id": effective_run_id},
                    "last_error": None,
                    "updated_at": None,
                },
            )
    return rows


def build_agent_tree(
    stored_agents: list[dict[str, object]],
    process_status: dict[str, object],
    *,
    max_parallel_workers: int,
) -> list[dict[str, object]]:
    rows = build_agent_overview_rows(
        stored_agents,
        process_status,
        max_parallel_workers=max_parallel_workers,
    )
    effective_run_id = (process_status.get("competition") or {}).get("run_id") or _infer_competition_run_id(rows)
    managers = [item for item in rows if item.get("role") == "manager"]
    workers = [item for item in rows if item.get("role") == "challenge_worker"]
    grouped: list[dict[str, object]] = []
    assigned: set[str] = set()

    for manager in managers:
        manager_id = str(manager["agent_id"])
        manager_run_id = (
            str((manager.get("metadata") or {}).get("run_id"))
            if (manager.get("metadata") or {}).get("run_id") is not None
            else manager_id.split(":")[-1]
        )
        children = [
            worker
            for worker in workers
            if (
                (worker.get("metadata") or {}).get("manager_agent_id") == manager_id
                or (worker.get("metadata") or {}).get("competition_run_id") == manager_run_id
            )
        ]
        assigned.update(str(item["agent_id"]) for item in children)
        grouped.append({"manager": manager, "workers": children})

    detached = [worker for worker in workers if str(worker["agent_id"]) not in assigned]
    if detached:
        for group in _build_archived_manager_groups(detached):
            grouped.append(group)
    return grouped


def _infer_competition_run_id(stored_agents: list[dict[str, object]]) -> str | None:
    manager_rows = [
        item
        for item in stored_agents
        if item.get("role") == "manager"
        and str(item.get("agent_id") or "").startswith("manager:competition:")
    ]
    if not manager_rows:
        return None
    manager_rows.sort(key=lambda item: ((item.get("updated_at") or ""), str(item.get("agent_id") or "")), reverse=True)
    metadata = dict(manager_rows[0].get("metadata") or {})
    run_id = metadata.get("run_id")
    if run_id is not None:
        return str(run_id)
    agent_id = str(manager_rows[0].get("agent_id") or "")
    return agent_id.split(":")[-1] if ":" in agent_id else None


def _build_archived_manager_groups(detached_workers: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped_workers: dict[str, list[dict[str, object]]] = {}
    manager_meta: dict[str, dict[str, object]] = {}

    for worker in detached_workers:
        metadata = dict(worker.get("metadata") or {})
        manager_id = str(metadata.get("manager_agent_id") or "").strip()
        if not manager_id:
            run_id = str(metadata.get("competition_run_id") or "").strip()
            manager_id = f"manager:competition:{run_id}" if run_id else "manager:detached"
        grouped_workers.setdefault(manager_id, []).append(worker)
        manager_meta.setdefault(
            manager_id,
            {
                "run_id": metadata.get("competition_run_id"),
                "synthetic": True,
            },
        )

    groups: list[dict[str, object]] = []
    for manager_id in sorted(grouped_workers):
        workers = grouped_workers[manager_id]
        if manager_id == "manager:detached":
            manager = {
                "agent_id": manager_id,
                "role": "manager",
                "status": "detached",
                "summary": "workers without a matching competition run",
                "metadata": {"synthetic": True},
            }
        else:
            manager = {
                "agent_id": manager_id,
                "role": "manager",
                "status": "archived",
                "summary": "historical workers from a previous competition run",
                "metadata": manager_meta[manager_id],
            }
        groups.append({"manager": manager, "workers": workers})
    return groups


def build_challenge_scheduler_view(
    challenge: dict[str, object],
    agent_statuses: list[dict[str, object]],
) -> dict[str, object]:
    code = str(challenge.get("code") or "")
    if challenge.get("completed") is True:
        return {
            "scheduler_status": "completed",
            "scheduler_reason": "official challenge state is completed",
            "assigned_workers": [],
        }

    notes = dict(challenge.get("notes") or {})
    runtime_state = dict(challenge.get("runtime_state") or {})
    assigned_workers = [
        str(agent["agent_id"])
        for agent in agent_statuses
        if agent.get("role") in {None, "challenge_worker"}
    ]

    if notes.get("operator_pause") == "true":
        return {
            "scheduler_status": "paused",
            "scheduler_reason": "challenge paused by operator",
            "assigned_workers": assigned_workers,
        }

    defer_until = runtime_state.get("defer_until")
    if defer_until not in (None, "") and float(defer_until) > time.time():
        return {
            "scheduler_status": "deferred",
            "scheduler_reason": "challenge temporarily deprioritized after a long-running attempt",
            "assigned_workers": assigned_workers,
        }

    active_statuses = [
        str(agent.get("status") or "")
        for agent in agent_statuses
        if agent.get("role") in {None, "challenge_worker"}
    ]
    if any(status in {"running", "pause_requested", "delete_requested"} for status in active_statuses):
        return {
            "scheduler_status": "running",
            "scheduler_reason": "worker currently assigned to this challenge",
            "assigned_workers": assigned_workers,
        }
    if any(status in {"error", "waiting_recovery"} for status in active_statuses):
        return {
            "scheduler_status": "retrying",
            "scheduler_reason": "worker previously failed and is waiting for another attempt",
            "assigned_workers": assigned_workers,
        }
    if any(status == "paused" for status in active_statuses):
        return {
            "scheduler_status": "paused",
            "scheduler_reason": "worker for this challenge is paused",
            "assigned_workers": assigned_workers,
        }

    return {
        "scheduler_status": "dispatchable",
        "scheduler_reason": f"unsolved challenge {code} with no assigned worker",
        "assigned_workers": assigned_workers,
    }
