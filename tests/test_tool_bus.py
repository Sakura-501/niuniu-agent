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
