from __future__ import annotations

import json
from typing import Any

from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from mcp.types import CallToolResult, TextContent

from niuniu_agent.config import AgentSettings


class ContestGateway:
    def __init__(self, server: MCPServerStreamableHttp) -> None:
        self.server = server

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
        result = await self.server.call_tool(name, arguments or {})
        if result.isError:
            raise RuntimeError(self.decode_call_result(result) or f"MCP call failed: {name}")
        return self.decode_call_result(result)

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
