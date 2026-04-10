from __future__ import annotations

import json
from typing import Any

from agents import RunContextWrapper, function_tool

from niuniu_agent.runtime.context import RuntimeContext


def build_local_tools() -> list[Any]:
    @function_tool
    async def get_challenge_overview(ctx: RunContextWrapper[RuntimeContext]) -> str:
        snapshot = await ctx.context.challenge_store.refresh()
        return ctx.context.challenge_store.render_summary(snapshot)

    @function_tool
    async def get_challenge_snapshot(ctx: RunContextWrapper[RuntimeContext]) -> str:
        snapshot = await ctx.context.challenge_store.refresh()
        return json.dumps(ctx.context.challenge_store.export_json(snapshot), ensure_ascii=False)

    @function_tool
    async def http_request(
        ctx: RunContextWrapper[RuntimeContext],
        method: str,
        url: str,
        body: str | None = None,
        timeout_seconds: int = 20,
    ) -> str:
        result = await ctx.context.local_toolbox.http_request(
            method=method,
            url=url,
            body=body,
            timeout_seconds=timeout_seconds,
        )
        return json.dumps(result, ensure_ascii=False)

    @function_tool
    async def run_shell_command(
        ctx: RunContextWrapper[RuntimeContext],
        command: str,
        timeout_seconds: int = 30,
    ) -> str:
        result = await ctx.context.local_toolbox.run_shell_command(
            command=command,
            timeout_seconds=timeout_seconds,
        )
        return json.dumps(result, ensure_ascii=False)

    @function_tool
    async def run_python_snippet(
        ctx: RunContextWrapper[RuntimeContext],
        code: str,
        timeout_seconds: int = 30,
    ) -> str:
        result = await ctx.context.local_toolbox.run_python_snippet(
            code=code,
            timeout_seconds=timeout_seconds,
        )
        return json.dumps(result, ensure_ascii=False)

    @function_tool
    async def get_local_runtime_state(ctx: RunContextWrapper[RuntimeContext]) -> str:
        snapshot = ctx.context.challenge_store.latest
        return json.dumps(
            {
                "snapshot": ctx.context.challenge_store.export_json(snapshot),
                "notes": ctx.context.notes,
            },
            ensure_ascii=False,
        )

    return [
        get_challenge_overview,
        get_challenge_snapshot,
        http_request,
        run_shell_command,
        run_python_snippet,
        get_local_runtime_state,
    ]
