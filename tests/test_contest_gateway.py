import asyncio

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


class InternallyCancelledServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        self.count += 1
        if self.count < 3:
            raise asyncio.CancelledError()
        return CallToolResult(
            content=[TextContent(type="text", text='{"current_level": 1, "challenges": []}')],
            isError=False,
        )


@pytest.mark.anyio
async def test_contest_gateway_retries_internal_cancelled_errors_for_list_challenges() -> None:
    sleeps = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    gateway = ContestGateway(InternallyCancelledServer(), sleep_fn=fake_sleep)

    payload = await gateway.list_challenges()

    assert payload["current_level"] == 1
    assert len(gateway.server.calls) == 3
    assert sleeps == [0.5, 1.0]


class PoolClosedServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.cleaned = False
        self.connected = False

    async def cleanup(self) -> None:
        self.cleaned = True

    async def connect(self) -> None:
        self.connected = True

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        raise RuntimeError("Cannot acquire connection after closing pool")


class ConnectedServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.connected = False

    async def connect(self) -> None:
        self.connected = True


class NotInitializedServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.cleaned = False
        self.connected = False

    async def cleanup(self) -> None:
        self.cleaned = True

    async def connect(self) -> None:
        self.connected = True

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        raise RuntimeError("Server not initialized. Make sure you call `connect()` first.")


class TimedOutServer(FakeServer):
    def __init__(self) -> None:
        super().__init__()
        self.cleaned = False

    async def cleanup(self) -> None:
        self.cleaned = True

    async def call_tool(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        raise RuntimeError("Timed out while waiting for response to ClientRequest. Waited 5.0 seconds.")


@pytest.mark.anyio
async def test_contest_gateway_rebuilds_server_after_pool_closed_error() -> None:
    created = []

    def server_factory():
        if not created:
            server = PoolClosedServer()
        else:
            server = ConnectedServer()
        created.append(server)
        return server

    gateway = ContestGateway(server_factory(), server_factory=server_factory)

    payload = await gateway.list_challenges()

    assert payload["current_level"] == 1
    assert len(created) == 2
    assert isinstance(created[0], PoolClosedServer)
    assert created[0].cleaned is True
    assert getattr(created[1], "connected", False) is True
    assert gateway.server is created[1]


@pytest.mark.anyio
async def test_contest_gateway_rebuilds_server_after_not_initialized_error() -> None:
    created = []

    def server_factory():
        if not created:
            server = NotInitializedServer()
        else:
            server = ConnectedServer()
        created.append(server)
        return server

    gateway = ContestGateway(server_factory(), server_factory=server_factory)

    payload = await gateway.list_challenges()

    assert payload["current_level"] == 1
    assert len(created) == 2
    assert isinstance(created[0], NotInitializedServer)
    assert created[0].cleaned is True
    assert getattr(created[1], "connected", False) is True


@pytest.mark.anyio
async def test_contest_gateway_rebuilds_server_after_timeout_error() -> None:
    created = []

    def server_factory():
        if not created:
            server = TimedOutServer()
        else:
            server = ConnectedServer()
        created.append(server)
        return server

    gateway = ContestGateway(server_factory(), server_factory=server_factory)

    payload = await gateway.list_challenges()

    assert payload["current_level"] == 1
    assert len(created) == 2
    assert isinstance(created[0], TimedOutServer)
    assert created[0].cleaned is True
    assert getattr(created[1], "connected", False) is True
