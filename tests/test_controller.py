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


@pytest.mark.anyio
async def test_controller_skips_already_submitted_flags(tmp_path) -> None:
    contest = DummyContestClient()
    store = StateStore(tmp_path / "state.db")
    store.record_submitted_flag("challenge-1", "flag{one}")

    controller = AgentController(
        settings=AgentSettings(
            model="ep-jsc7o0kw",
            model_base_url="https://tokenhub.tencentmaas.com/v1",
            model_api_key="test-key",
            contest_host="10.0.0.44:8000",
            contest_token="token",
            runtime_dir=tmp_path / "runtime",
        ),
        contest_client=contest,
        state_store=store,
        event_logger=EventLogger(tmp_path / "events.jsonl"),
        router=StrategyRouter.default(),
        toolbox=LocalToolbox(tmp_path / "runtime"),
        solver=None,
    )

    submitted = await controller.submit_candidate_flags(
        "challenge-1",
        ["flag{one}", "flag{two}", "flag{two}"],
    )

    assert submitted == ["flag{two}"]
    assert contest.submissions == [("challenge-1", "flag{two}")]
