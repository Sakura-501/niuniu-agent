from mcp.types import CallToolResult, TextContent

from niuniu_agent.contest_mcp import ContestMCPClient


def test_normalize_entrypoints() -> None:
    assert ContestMCPClient.normalize_entrypoints(["127.0.0.1:8080"]) == ["127.0.0.1:8080"]
    assert ContestMCPClient.normalize_entrypoints(None) == []
    assert ContestMCPClient.normalize_entrypoints({"already_completed": True}) == []


def test_decode_call_result_prefers_json_text() -> None:
    result = CallToolResult(
        content=[
            TextContent(type="text", text='{"code": 0, "message": "success", "data": ["127.0.0.1:8080"]}'),
        ],
        isError=False,
    )

    payload = ContestMCPClient.decode_call_result(result)

    assert payload["code"] == 0
    assert payload["data"] == ["127.0.0.1:8080"]
