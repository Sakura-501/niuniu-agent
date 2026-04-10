from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent


class ContestMCPClient:
    def __init__(self, url: str, token: str, timeout_seconds: int = 30) -> None:
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "ContestMCPClient":
        self._stack = AsyncExitStack()
        read_stream, write_stream, _ = await self._stack.enter_async_context(
            streamablehttp_client(
                self.url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout_seconds,
            )
        )
        self._session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    @staticmethod
    def normalize_entrypoints(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    @staticmethod
    def decode_call_result(result: CallToolResult) -> Any:
        if result.structuredContent is not None:
            return result.structuredContent

        text_parts = [item.text for item in result.content if isinstance(item, TextContent)]
        if not text_parts:
            return None

        text = "\n".join(text_parts)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    async def list_challenges(self) -> Any:
        return await self._call("list_challenges")

    async def start_challenge(self, code: str) -> Any:
        return await self._call("start_challenge", {"code": code})

    async def stop_challenge(self, code: str) -> Any:
        return await self._call("stop_challenge", {"code": code})

    async def submit_flag(self, code: str, flag: str) -> Any:
        return await self._call("submit_flag", {"code": code, "flag": flag})

    async def view_hint(self, code: str) -> Any:
        return await self._call("view_hint", {"code": code})

    async def _call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if self._session is None:
            raise RuntimeError("ContestMCPClient is not connected")

        result = await self._session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError(self.decode_call_result(result) or f"MCP call failed: {name}")
        return self.decode_call_result(result)
