import pytest

from mcp.types import CallToolResult, TextContent

from niuniu_agent.control_plane.contest_gateway import ContestGateway


class FakeServer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def connect(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return CallToolResult(
            content=[TextContent(type="text", text='{"current_level": 1, "challenges": []}')],
            isError=False,
        )


@pytest.mark.anyio
async def test_contest_gateway_uses_openai_agents_mcp_server() -> None:
    gateway = ContestGateway(FakeServer())

    payload = await gateway.list_challenges()

    assert payload["current_level"] == 1
    assert gateway.server.calls == [("list_challenges", {})]


class RateLimitedServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        self.count += 1
        if self.count < 3:
            return CallToolResult(
                content=[TextContent(type="text", text="Error calling tool 'list_challenges': 请求频率超出限制，每秒最多调用3次")],
                isError=True,
            )
        return CallToolResult(
            content=[TextContent(type="text", text='{"current_level": 1, "challenges": []}')],
            isError=False,
        )


@pytest.mark.anyio
async def test_contest_gateway_retries_rate_limited_list_challenges() -> None:
    sleeps = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    gateway = ContestGateway(RateLimitedServer(), sleep_fn=fake_sleep)

    payload = await gateway.list_challenges()

    assert payload["current_level"] == 1
    assert len(gateway.server.calls) == 3
    assert sleeps == [0.5, 1.0]
