import json

import pytest

from niuniu_agent.agent_stack.tool_bus import ToolBus
from niuniu_agent.config import AgentSettings
from niuniu_agent.control_plane.challenge_store import ChallengeStore
from niuniu_agent.runtime.context import RuntimeContext
from niuniu_agent.state_store import StateStore
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox
from niuniu_agent.skills import SkillRegistry


class DummyContestGateway:
    async def list_challenges(self):
        return {"current_level": 1, "challenges": []}

    async def start_challenge(self, code: str):
        return {"code": 0}

    async def stop_challenge(self, code: str):
        return {"code": 0}

    async def submit_flag(self, code: str, flag: str):
        return {"code": 0}

    async def view_hint(self, code: str):
        return {"code": 0}


@pytest.mark.anyio
async def test_tool_bus_exposes_history_and_note_tools(tmp_path) -> None:
    gateway = DummyContestGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    await bus.set_challenge_note("c1", "foothold", "user shell")
    history = await bus.get_challenge_history("c1")
    notes = await bus.get_challenge_notes("c1")

    assert history["history"] == []
    assert notes["notes"]["foothold"] == "user shell"


@pytest.mark.anyio
async def test_tool_bus_reuses_cached_tool_schema_list(tmp_path) -> None:
    gateway = DummyContestGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    first = bus.tool_schemas()
    second = bus.tool_schemas()

    assert first is second


@pytest.mark.anyio
async def test_tool_bus_exposes_challenge_memory_tools(tmp_path) -> None:
    gateway = DummyContestGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)
    state_store.add_challenge_memory("c1", "turn_summary", "found login page", source="worker")

    memories = await bus.get_challenge_memories("c1")

    assert memories["memories"][0]["memory_type"] == "turn_summary"


@pytest.mark.anyio
async def test_tool_bus_returns_error_string_instead_of_raising(tmp_path) -> None:
    class RaisingGateway(DummyContestGateway):
        async def view_hint(self, code: str):
            raise RuntimeError("赛题实例未运行，请先启动赛题")

    gateway = RaisingGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.dispatch("view_hint", {"code": "c1"})

    assert "Error calling tool 'view_hint'" in result
    assert "赛题实例未运行" in result


@pytest.mark.anyio
async def test_tool_bus_stop_challenge_is_idempotent_when_instance_not_running(tmp_path) -> None:
    class StopGateway(DummyContestGateway):
        async def stop_challenge(self, code: str):
            raise RuntimeError("赛题实例未运行，请先启动赛题")

    gateway = StopGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.stop_challenge("c1")

    assert result["code"] == "c1"
    assert result["already_stopped"] is True
    assert "payload" not in result


@pytest.mark.anyio
async def test_tool_bus_auto_submits_detected_flags_from_tool_output(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.submit_calls = []

        async def submit_flag(self, code: str, flag: str):
            self.submit_calls.append((code, flag))
            return {"correct": True, "message": "恭喜！答案正确"}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "demo",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 1,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            return {"code": 0}

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
        challenge_code="c1",
    )
    bus = ToolBus(context)

    async def fake_run_python_snippet(code: str, timeout_seconds: int = 30):
        return {"exit_code": 0, "stdout": "found flag{demo}", "stderr": ""}

    bus._handlers["run_python_snippet"] = fake_run_python_snippet
    result = json.loads(await bus.dispatch("run_python_snippet", {"code": "print(1)"}))

    assert gateway.submit_calls == [("c1", "flag{demo}")]
    assert result["auto_submitted_flags"][0]["flag"] == "flag{demo}"


@pytest.mark.anyio
async def test_tool_bus_dispatches_webshell_exec_and_auto_submits_flags(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.submit_calls = []

        async def submit_flag(self, code: str, flag: str):
            self.submit_calls.append((code, flag))
            return {"correct": True, "message": "correct"}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "demo",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 2,
                        "flag_got_count": 1,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            return {"code": 0}

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
        challenge_code="c1",
    )
    bus = ToolBus(context)

    async def fake_webshell_exec(**kwargs):
        return {"status_code": 200, "headers": {}, "text": "flag{demo2}", "marker_found": False}

    bus._handlers["webshell_exec"] = fake_webshell_exec
    result = json.loads(await bus.dispatch("webshell_exec", {"url": "http://target/uploads/shell.php", "command": "cat /challenge/flag2.txt"}))

    assert gateway.submit_calls == [("c1", "flag{demo2}")]
    assert result["auto_submitted_flags"][0]["flag"] == "flag{demo2}"


@pytest.mark.anyio
async def test_tool_bus_auto_submits_even_if_flag_was_previously_recorded(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.submit_calls = []

        async def submit_flag(self, code: str, flag: str):
            self.submit_calls.append((code, flag))
            return {"correct": True, "message": "correct"}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "demo",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 1,
                        "instance_status": "stopped",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    state_store.record_submitted_flag("c1", "flag{demo}")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
        challenge_code="c1",
    )
    bus = ToolBus(context)

    async def fake_http_request(method: str, url: str, body: str | None = None, timeout_seconds: int = 20):
        return {"status_code": 200, "text": "flag{demo}"}

    bus._handlers["http_request"] = fake_http_request
    await bus.dispatch("http_request", {"method": "GET", "url": "http://example.com"})

    assert gateway.submit_calls == [("c1", "flag{demo}")]


@pytest.mark.anyio
async def test_tool_bus_auto_submits_flags_found_in_assistant_text(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.submit_calls = []

        async def submit_flag(self, code: str, flag: str):
            self.submit_calls.append((code, flag))
            return {"correct": True, "message": "correct"}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "demo",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 2,
                        "flag_got_count": 1,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            return {"code": 0}

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
        challenge_code="c1",
    )
    bus = ToolBus(context)

    result = await bus.auto_submit_text_output("assistant found flag{demo1} and flag{demo2}")

    assert ("c1", "flag{demo1}") in gateway.submit_calls
    assert ("c1", "flag{demo2}") in gateway.submit_calls
    assert len(result) == 2


@pytest.mark.anyio
async def test_tool_bus_view_hint_persists_hint_notes_history_and_memory(tmp_path) -> None:
    class HintGateway(DummyContestGateway):
        async def view_hint(self, code: str):
            return {"payload": {"hint": "look at the proxy filter first"}}

    gateway = HintGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
        agent_id="worker:c1",
        challenge_code="c1",
    )
    bus = ToolBus(context)

    payload = await bus.view_hint("c1")

    assert payload["hint_context"]["hint_viewed"] is True
    assert payload["hint_context"]["hint_content"] == "look at the proxy filter first"
    assert state_store.get_challenge_notes("c1")["hint_content"] == "look at the proxy filter first"
    history = state_store.list_history("c1", limit=5)
    assert history[0]["event_type"] == "hint_viewed"
    memories = state_store.list_challenge_memories("c1", limit=5)
    assert memories[0]["memory_type"] == "persistent_hint"
    assert memories[0]["persistent"] is True


@pytest.mark.anyio
async def test_tool_bus_start_challenge_handles_instance_limit(tmp_path) -> None:
    class LimitedGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.start_calls = 0
            self.stopped = []

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "demo1",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "running one",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "running",
                        "entrypoint": None,
                    },
                    {
                        "title": "demo2",
                        "code": "c2",
                        "difficulty": "easy",
                        "description": "target",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    },
                ],
            }

        async def start_challenge(self, code: str):
            self.start_calls += 1
            if self.start_calls == 1:
                raise RuntimeError("最多同时运行3个实例，请先停止其他实例")
            return {"entrypoint": ["127.0.0.1:8080"]}

        async def stop_challenge(self, code: str):
            self.stopped.append(code)
            return {"code": 0}

    gateway = LimitedGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.start_challenge("c2")

    assert gateway.stopped == ["c1"]
    assert result["stopped"] == ["c1"]
    assert result["payload"]["entrypoint"] == ["127.0.0.1:8080"]


@pytest.mark.anyio
async def test_tool_bus_start_challenge_proactively_frees_slots(tmp_path) -> None:
    class BusyGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.stopped = []

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {"title": "a", "code": "c1", "difficulty": "easy", "description": "", "level": 1, "flag_count": 1, "flag_got_count": 0, "instance_status": "running", "entrypoint": None},
                    {"title": "b", "code": "c2", "difficulty": "easy", "description": "", "level": 1, "flag_count": 1, "flag_got_count": 0, "instance_status": "running", "entrypoint": None},
                    {"title": "c", "code": "c3", "difficulty": "easy", "description": "", "level": 1, "flag_count": 1, "flag_got_count": 0, "instance_status": "running", "entrypoint": None},
                    {"title": "d", "code": "c4", "difficulty": "easy", "description": "", "level": 1, "flag_count": 1, "flag_got_count": 0, "instance_status": "stopped", "entrypoint": None},
                ],
            }

        async def stop_challenge(self, code: str):
            self.stopped.append(code)
            return {"code": 0}

        async def start_challenge(self, code: str):
            return {"entrypoint": ["127.0.0.1:8080"]}

    gateway = BusyGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.start_challenge("c4")

    assert gateway.stopped == ["c1", "c2", "c3"]
    assert result["running_count_before"] == 3
    assert result["stopped"] == ["c1", "c2", "c3"]


@pytest.mark.anyio
async def test_tool_bus_submit_flag_stops_completed_instance(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.stopped = []

        async def submit_flag(self, code: str, flag: str):
            return {"code": 0}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "done",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 1,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            self.stopped.append(code)
            return {"code": 0}

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.submit_flag("c1", "flag{demo}")

    assert result["completed"] is True
    assert result["stopped_instance"] is True
    assert gateway.stopped == ["c1"]


@pytest.mark.anyio
async def test_tool_bus_submit_flag_records_success_from_correct_payload(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        async def submit_flag(self, code: str, flag: str):
            return {"correct": True, "message": "恭喜！答案正确"}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "done",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 1,
                        "instance_status": "stopped",
                        "entrypoint": None,
                    }
                ],
            }

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    await bus.submit_flag("c1", "flag{demo}")

    assert state_store.has_submitted_flag("c1", "flag{demo}") is True
    notes = state_store.get_challenge_notes("c1")
    assert notes["last_flag"] == "flag{demo}"
    history = state_store.list_history("c1")
    assert history[0]["event_type"] == "flag_submitted"


@pytest.mark.anyio
async def test_tool_bus_submit_flag_uses_local_completion_when_official_snapshot_lags(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        async def submit_flag(self, code: str, flag: str):
            return {"correct": True, "message": "恭喜！答案正确"}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "lagging",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 0,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            return {"code": 0}

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.submit_flag("c1", "flag{demo}")

    assert result["completed"] is True


@pytest.mark.anyio
async def test_tool_bus_submit_flag_persists_high_track_flag_memory_without_marking_complete_when_flag_count_unknown(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        async def submit_flag(self, code: str, flag: str):
            return {"correct": True, "message": "correct", "payload": {"flag_count": 4, "flag_got_count": 1}}

        async def list_challenges(self):
            return {
                "current_level": 3,
                "challenges": [
                    {
                        "title": "multi",
                        "code": "c1",
                        "difficulty": "hard",
                        "description": "pivot internal foothold",
                        "level": 2,
                        "flag_count": 0,
                        "flag_got_count": 0,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            raise AssertionError("should not stop high-track instance after one local flag")

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    state_store.set_challenge_note("c1", "provisional_findings", "use proxy.php first")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.submit_flag("c1", "flag{demo}")
    memories = state_store.list_challenge_memories("c1", limit=10)

    assert result["completed"] is False
    assert any(item["memory_type"] == "persistent_flag_record" and item["persistent"] is True for item in memories)


@pytest.mark.anyio
async def test_tool_bus_submit_flag_persists_short_flag_record_only(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        async def submit_flag(self, code: str, flag: str):
            return {
                "correct": True,
                "payload": {
                    "flag_count": 4,
                    "flag_got_count": 2,
                    "message": "correct",
                },
            }

        async def list_challenges(self):
            return {
                "current_level": 3,
                "challenges": [
                    {
                        "title": "track3",
                        "code": "6RmRST2HkeTbwgbyMJaN",
                        "difficulty": "medium",
                        "description": "pivot internal foothold track3",
                        "level": 3,
                        "flag_count": 4,
                        "flag_got_count": 2,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

        async def stop_challenge(self, code: str):
            return {"code": 0}

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    state_store.set_challenge_note("6RmRST2HkeTbwgbyMJaN", "provisional_findings", "old noisy note")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    await bus.submit_flag("6RmRST2HkeTbwgbyMJaN", "flag{demo}")

    record = next(
        item for item in state_store.list_challenge_memories("6RmRST2HkeTbwgbyMJaN", limit=20)
        if item["memory_type"] == "persistent_flag_record" and item["source"] == "submit_flag"
    )

    assert record["content"] == "flag=flag{demo}\nprogress=2/4"


@pytest.mark.anyio
async def test_tool_bus_submit_flag_starts_instance_when_needed(tmp_path) -> None:
    class SubmitGateway(DummyContestGateway):
        def __init__(self) -> None:
            self.start_calls = 0
            self.submit_calls = 0

        async def submit_flag(self, code: str, flag: str):
            self.submit_calls += 1
            if self.submit_calls == 1:
                raise RuntimeError("赛题实例未运行，请先启动赛题")
            return {"correct": True, "message": "恭喜！答案正确"}

        async def start_challenge(self, code: str):
            self.start_calls += 1
            return {"entrypoint": ["127.0.0.1:8080"]}

        async def list_challenges(self):
            return {
                "current_level": 1,
                "challenges": [
                    {
                        "title": "done",
                        "code": "c1",
                        "difficulty": "easy",
                        "description": "",
                        "level": 1,
                        "flag_count": 1,
                        "flag_got_count": 1,
                        "instance_status": "running",
                        "entrypoint": ["127.0.0.1:8080"],
                    }
                ],
            }

    gateway = SubmitGateway()
    state_store = StateStore(tmp_path / "state.db")
    challenge_store = ChallengeStore(gateway, state_store)
    context = RuntimeContext(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
        ),
        contest_gateway=gateway,
        challenge_store=challenge_store,
        state_store=state_store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        local_toolbox=LocalToolbox(tmp_path / "runtime"),
        skill_registry=SkillRegistry(),
    )
    bus = ToolBus(context)

    result = await bus.submit_flag("c1", "flag{demo}")

    assert gateway.start_calls == 1
    assert gateway.submit_calls == 2
    assert result["completed"] is True
