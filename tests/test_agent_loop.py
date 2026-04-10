import pytest

from agents.exceptions import MaxTurnsExceeded

from niuniu_agent.runtime.agent_loop import run_until_final_output


class DummyResult:
    def __init__(self, text: str) -> None:
        self._text = text

    def final_output_as(self, _type):
        return self._text


@pytest.mark.anyio
async def test_run_until_final_output_retries_after_max_turns(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_run(agent, input, **kwargs):
        calls.append(input)
        if len(calls) == 1:
            raise MaxTurnsExceeded("chunk exhausted")
        return DummyResult("final answer")

    monkeypatch.setattr("niuniu_agent.runtime.agent_loop.Runner.run", fake_run)

    result = await run_until_final_output(
        agent=object(),
        initial_input="start here",
        context=object(),
        session=object(),
        hooks=None,
        event_logger=None,
    )

    assert result.final_output_as(str) == "final answer"
    assert calls[0] == "start here"
    assert "Continue from the current state" in calls[1]
