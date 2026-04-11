from __future__ import annotations

import asyncio
import json
from typing import Any

from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from mcp.types import CallToolResult, TextContent

from niuniu_agent.config import AgentSettings


class ContestGateway:
    def __init__(
        self,
        server: MCPServerStreamableHttp,
        *,
        sleep_fn: Any | None = None,
    ) -> None:
        self.server = server
        self._sleep = sleep_fn or asyncio.sleep
        self._list_challenges_lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings: AgentSettings) -> "ContestGateway":
        server = MCPServerStreamableHttp(
            params=MCPServerStreamableHttpParams(
                url=settings.contest_mcp_url,
                headers={"Authorization": f"Bearer {settings.contest_token}"},
            ),
            name="contest-mcp",
            cache_tools_list=True,
            max_retry_attempts=2,
        )
        return cls(server)

    async def connect(self) -> None:
        await self.server.connect()

    async def cleanup(self) -> None:
        await self.server.cleanup()

    async def list_challenges(self) -> Any:
        async with self._list_challenges_lock:
            return await self._call_with_rate_limit_retry("list_challenges")

    async def start_challenge(self, code: str) -> Any:
        return await self._call("start_challenge", {"code": code})

    async def stop_challenge(self, code: str) -> Any:
        return await self._call("stop_challenge", {"code": code})

    async def submit_flag(self, code: str, flag: str) -> Any:
        return await self._call("submit_flag", {"code": code, "flag": flag})

    async def view_hint(self, code: str) -> Any:
        return await self._call("view_hint", {"code": code})

    async def _call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = await self.server.call_tool(name, arguments or {})
        if result.isError:
            raise RuntimeError(self.decode_call_result(result) or f"MCP call failed: {name}")
        return self.decode_call_result(result)

    async def _call_with_rate_limit_retry(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        max_attempts: int = 3,
    ) -> Any:
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return await self._call(name, arguments)
            except RuntimeError as exc:
                last_error = exc
                if "请求频率超出限制" not in str(exc) or attempt >= max_attempts:
                    raise
                await self._sleep(delay)
                delay *= 2
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"MCP call failed without error details: {name}")

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
