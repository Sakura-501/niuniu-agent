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
            model_base_url="https://tokenhub.tencentmaas.com/v1",
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
            model_base_url="https://tokenhub.tencentmaas.com/v1",
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
            model_base_url="https://tokenhub.tencentmaas.com/v1",
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
            model_base_url="https://tokenhub.tencentmaas.com/v1",
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
            model_base_url="https://tokenhub.tencentmaas.com/v1",
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
            model_base_url="https://tokenhub.tencentmaas.com/v1",
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
