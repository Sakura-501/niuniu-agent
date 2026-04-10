import pytest

from niuniu_agent.runtime.findings_bus import ChallengeFindingsBus


@pytest.mark.anyio
async def test_findings_bus_shares_findings_between_workers() -> None:
    bus = ChallengeFindingsBus()

    await bus.post("c1", "worker:a", "发现了登录入口")
    unread = await bus.check("c1", "worker:b")

    assert len(unread) == 1
    assert unread[0].content == "发现了登录入口"
    assert "worker:a" in bus.format_unread(unread)
