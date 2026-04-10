import pytest

from niuniu_agent.config import AgentSettings
from niuniu_agent.controller import AgentController
from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.router import StrategyRouter
from niuniu_agent.telemetry import EventLogger
from niuniu_agent.tooling import LocalToolbox


class DummyContestClient:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, str]] = []

    async def submit_flag(self, code: str, flag: str) -> dict[str, int | str]:
        self.submissions.append((code, flag))
        return {"code": 0, "message": "success"}


def build_controller(tmp_path, contest=None) -> AgentController:
    return AgentController(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="https://tokenhub.tencentmaas.com/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
            runtime_dir=tmp_path / "runtime",
        ),
        contest_client=contest or DummyContestClient(),
        state_store=StateStore(tmp_path / "state.db"),
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        router=StrategyRouter.default(),
        toolbox=LocalToolbox(tmp_path / "runtime"),
        solver=None,
    )


@pytest.mark.anyio
async def test_controller_skips_already_submitted_flags(tmp_path) -> None:
    contest = DummyContestClient()
    controller = build_controller(tmp_path, contest=contest)
    store = controller.state_store
    store.record_submitted_flag("challenge-1", "flag{one}")

    submitted = await controller.submit_candidate_flags(
        "challenge-1",
        ["flag{one}", "flag{two}", "flag{two}"],
    )

    assert submitted == ["flag{two}"]
    assert contest.submissions == [("challenge-1", "flag{two}")]


def test_controller_parses_root_level_mcp_payload(tmp_path) -> None:
    controller = build_controller(tmp_path)

    challenges = controller.parse_challenges(
        {
            "current_level": 1,
            "challenges": [
                {
                    "title": "demo",
                    "code": "abc",
                    "difficulty": "easy",
                    "description": "welcome",
                    "level": 0,
                    "flag_count": 1,
                    "flag_got_count": 0,
                    "instance_status": "stopped",
                    "entrypoint": None,
                }
            ],
        }
    )

    assert len(challenges) == 1
    assert challenges[0].code == "abc"
    assert challenges[0].flag_count == 1
