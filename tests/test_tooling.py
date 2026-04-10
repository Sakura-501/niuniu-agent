from niuniu_agent.tooling import LocalToolbox


def test_http_tool_schema_contains_method_and_url(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    tools = {
        entry["function"]["name"]: entry
        for entry in toolbox.describe_tools()
    }

    http_tool = tools["http_request"]
    properties = http_tool["function"]["parameters"]["properties"]

    assert "method" in properties
    assert "url" in properties


def test_extract_flags_deduplicates_matches(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    flags = toolbox.extract_flags("flag{one} ignore flag{one} and flag{two}")

    assert flags == ["flag{one}", "flag{two}"]


import pytest


@pytest.mark.anyio
async def test_run_shell_command_falls_back_for_missing_curl(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    monkeypatch.setattr("niuniu_agent.tooling.shutil.which", lambda name: None if name == "curl" else "/usr/bin/true")

    async def fake_http_request(method, url, body=None, timeout_seconds=20):
        return {"status_code": 200, "text": "ok"}

    monkeypatch.setattr(toolbox, "http_request", fake_http_request)

    result = await toolbox.run_shell_command("curl http://example.com")

    assert result["fallback_used"] is True
    assert result["exit_code"] == 0
    assert "status_code" in result["stdout"]


@pytest.mark.anyio
async def test_run_shell_command_falls_back_for_missing_ffuf(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    monkeypatch.setattr("niuniu_agent.tooling.shutil.which", lambda name: None if name == "ffuf" else "/usr/bin/true")

    async def fake_http_request(method, url, body=None, timeout_seconds=20):
        return {"status_code": 200, "text": url}

    monkeypatch.setattr(toolbox, "http_request", fake_http_request)

    result = await toolbox.run_shell_command("ffuf -u http://example.com/FUZZ")

    assert result["fallback_used"] is True
    assert "findings" in result["stdout"]
