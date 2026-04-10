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
