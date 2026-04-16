import asyncio
from pathlib import Path

import httpx
import pytest
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


def test_http_tool_schema_includes_headers_params_and_files_and_webshell_exec(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    tools = {
        entry["function"]["name"]: entry
        for entry in toolbox.describe_tools()
    }

    http_tool = tools["http_request"]
    webshell_tool = tools["webshell_exec"]

    http_properties = http_tool["function"]["parameters"]["properties"]
    webshell_properties = webshell_tool["function"]["parameters"]["properties"]

    assert "headers" in http_properties
    assert "params" in http_properties
    assert "cookies" in http_properties
    assert "form" in http_properties
    assert "files" in http_properties
    assert "url" in webshell_properties
    assert "command" in webshell_properties
    assert "param_name" in webshell_properties
    assert "expect_marker" in webshell_properties


def test_extract_flags_deduplicates_matches(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    flags = toolbox.extract_flags("flag{one} ignore flag{one} and flag{two}")

    assert flags == ["flag{one}", "flag{two}"]


def test_extract_flags_ignores_non_braced_flag_like_tokens(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    flags = toolbox.extract_flags(
        "candidate FLAG-9f8e7d6c5b4a and api returned token=flagABCDEF12345678 plus flag_count should be ignored"
    )

    assert flags == []


@pytest.mark.anyio
async def test_http_request_surfaces_exception_type_and_message(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, *args, **kwargs):
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("niuniu_agent.tooling.httpx.AsyncClient", FakeClient)

    with pytest.raises(RuntimeError, match="ReadTimeout: timed out"):
        await toolbox.http_request("GET", "http://example.com")


@pytest.mark.anyio
async def test_http_request_forwards_headers_params_cookies_form_and_files(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    seen = {}

    class DummyResponse:
        status_code = 200
        headers = {"x-test": "ok"}
        text = "done"

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, *args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs
            return DummyResponse()

    monkeypatch.setattr("niuniu_agent.tooling.httpx.AsyncClient", FakeClient)

    result = await toolbox.http_request(
        "POST",
        "http://example.com/upload",
        headers={"X-Test": "1"},
        params={"a": "b"},
        cookies={"sid": "demo"},
        form={"name": "demo"},
        files=[{"name": "attachment", "filename": "shell.php", "content": "<?php echo 1; ?>", "content_type": "application/x-php"}],
    )

    assert result["status_code"] == 200
    assert seen["kwargs"]["headers"] == {"X-Test": "1"}
    assert seen["kwargs"]["params"] == {"a": "b"}
    assert seen["kwargs"]["cookies"] == {"sid": "demo"}
    assert seen["kwargs"]["data"] == {"name": "demo"}
    assert seen["kwargs"]["files"][0][0] == "attachment"
    assert seen["kwargs"]["files"][0][1][0] == "shell.php"


@pytest.mark.anyio
async def test_webshell_exec_wraps_http_request_and_detects_marker(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    seen = {}

    async def fake_http_request(method, url, **kwargs):
        seen["method"] = method
        seen["url"] = url
        seen["kwargs"] = kwargs
        return {"status_code": 200, "headers": {}, "text": "uid=33(www-data)"}

    monkeypatch.setattr(toolbox, "http_request", fake_http_request)

    result = await toolbox.webshell_exec(
        url="http://target/uploads/shell.php",
        command="id",
        expect_marker="www-data",
        headers={"Cookie": "PHPSESSID=demo"},
        params={"a": "b"},
    )

    assert result["status_code"] == 200
    assert result["marker_found"] is True
    assert seen["method"] == "GET"
    assert seen["kwargs"]["params"]["a"] == "b"
    assert seen["kwargs"]["params"]["cmd"] == "id"

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


@pytest.mark.anyio
async def test_run_shell_command_prefers_uv_for_python_commands(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    seen = {}

    monkeypatch.setattr("niuniu_agent.tooling.shutil.which", lambda name: "/usr/bin/uv" if name == "uv" else "/usr/bin/true")

    class DummyProcess:
        returncode = 0

        async def communicate(self):
            return b"ok", b""

    async def fake_subprocess(command, **kwargs):
        seen["command"] = command
        return DummyProcess()

    monkeypatch.setattr("niuniu_agent.tooling.asyncio.create_subprocess_shell", fake_subprocess)

    result = await toolbox.run_shell_command("python3 /tmp/demo.py")

    assert result["exit_code"] == 0
    assert seen["command"].startswith("uv run python ")


@pytest.mark.anyio
async def test_run_python_snippet_prefers_uv_python(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    seen = {}

    monkeypatch.setattr("niuniu_agent.tooling.shutil.which", lambda name: "/usr/bin/uv" if name == "uv" else "/usr/bin/true")

    async def fake_run_shell_command(command, **kwargs):
        seen["command"] = command
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    monkeypatch.setattr(toolbox, "run_shell_command", fake_run_shell_command)

    result = await toolbox.run_python_snippet("print('hi')")

    assert result["exit_code"] == 0
    assert seen["command"].startswith("uv run python ")


@pytest.mark.anyio
async def test_run_shell_command_kills_process_when_cancelled(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    seen = {}

    class DummyProcess:
        returncode = None

        def __init__(self) -> None:
            self.killed = False

        async def communicate(self):
            await asyncio.Event().wait()

        def kill(self):
            self.killed = True

    process = DummyProcess()

    async def fake_subprocess(command, **kwargs):
        seen["command"] = command
        return process

    monkeypatch.setattr("niuniu_agent.tooling.asyncio.create_subprocess_shell", fake_subprocess)

    task = asyncio.create_task(toolbox.run_shell_command("sleep 60"))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert process.killed is True


@pytest.mark.anyio
async def test_run_shell_command_prepends_managed_bin_dir_to_path(monkeypatch, tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    seen = {}

    class DummyProcess:
        returncode = 0

        async def communicate(self):
            return b"ok", b""

    async def fake_subprocess(command, **kwargs):
        seen["env"] = kwargs.get("env", {})
        return DummyProcess()

    monkeypatch.setattr("niuniu_agent.tooling.asyncio.create_subprocess_shell", fake_subprocess)

    result = await toolbox.run_shell_command("echo ok")

    assert result["exit_code"] == 0
    assert str(toolbox.managed_bin_dir) in seen["env"]["PATH"]


@pytest.mark.anyio
async def test_run_shell_command_timeout_kills_background_children(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)
    marker = Path(tmp_path) / "late-child.txt"
    command = (
        "sh -c '"
        f"(sleep 2; echo late > {marker}) & "
        "sleep 30"
        "'"
    )

    result = await toolbox.run_shell_command(command, timeout_seconds=1)

    assert result["exit_code"] == -1
    await asyncio.sleep(3)
    assert marker.exists() is False
