import pytest

from niuniu_agent.config import AgentSettings
from niuniu_agent.controller import AgentController
from niuniu_agent.debug_chat import DebugToolbox
from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.router import StrategyRouter
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox


class DummyContestClient:
    async def list_challenges(self):
        return {
            "current_level": 2,
            "challenges": [
                {
                    "title": "demo 1",
                    "code": "c1",
                    "difficulty": "easy",
                    "description": "welcome",
                    "level": 1,
                    "flag_count": 1,
                    "flag_got_count": 1,
                    "instance_status": "stopped",
                    "entrypoint": None,
                },
                {
                    "title": "demo 2",
                    "code": "c2",
                    "difficulty": "medium",
                    "description": "web portal",
                    "level": 2,
                    "flag_count": 2,
                    "flag_got_count": 0,
                    "instance_status": "running",
                    "entrypoint": ["127.0.0.1:8080"],
                },
            ],
        }

    async def start_challenge(self, code: str):
        return ["127.0.0.1:8080"]

    async def stop_challenge(self, code: str):
        return {"code": 0}

    async def submit_flag(self, code: str, flag: str):
        return {"code": 0}

    async def view_hint(self, code: str):
        return {"code": 0, "data": "hint"}


def build_controller(tmp_path, contest_client) -> AgentController:
    return AgentController(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="https://tokenhub.tencentmaas.com/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
            runtime_dir=tmp_path / "runtime",
        ),
        contest_client=contest_client,
        state_store=StateStore(tmp_path / "state.db"),
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        router=StrategyRouter.default(),
        toolbox=LocalToolbox(tmp_path / "runtime"),
        solver=None,
    )


@pytest.mark.anyio
async def test_debug_toolbox_lists_challenge_status_with_local_flags(tmp_path) -> None:
    contest_client = DummyContestClient()
    controller = build_controller(tmp_path, contest_client)
    controller.state_store.record_submitted_flag("c2", "flag{debug}")
    toolbox = DebugToolbox(controller=controller)

    payload = await toolbox.list_challenges()

    assert payload["current_level"] == 2
    assert payload["challenges"][0]["completed"] is True
    assert payload["challenges"][1]["locally_submitted_flags"] == ["flag{debug}"]


def test_debug_toolbox_exposes_contest_and_local_tools(tmp_path) -> None:
    contest_client = DummyContestClient()
    controller = build_controller(tmp_path, contest_client)
    toolbox = DebugToolbox(controller=controller)

    tool_names = {
        tool["function"]["name"]
        for tool in toolbox.describe_tools()
    }

    assert "list_challenges" in tool_names
    assert "start_challenge" in tool_names
    assert "http_request" in tool_names
