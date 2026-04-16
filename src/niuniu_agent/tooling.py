from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shlex
import shutil
import signal
import tempfile
from pathlib import Path
from typing import Any

import httpx

from niuniu_agent.tools_inventory import default_tool_inventory


class LocalToolbox:
    def __init__(self, runtime_dir: Path) -> None:
        self.runtime_dir = runtime_dir
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.managed_bin_dir = Path(__file__).resolve().parents[2] / "tools" / "bin"

    def describe_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_tool_inventory",
                    "description": "List which local tools are available and how to install missing ones.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "http_request",
                    "description": "Send an HTTP request to a challenge endpoint.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string"},
                            "url": {"type": "string"},
                            "headers": {"type": "object", "additionalProperties": {"type": "string"}},
                            "params": {"type": "object", "additionalProperties": {"type": "string"}},
                            "cookies": {"type": "object", "additionalProperties": {"type": "string"}},
                            "form": {"type": "object", "additionalProperties": {"type": "string"}},
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "filename": {"type": "string"},
                                        "content": {"type": "string"},
                                        "content_type": {"type": "string"},
                                    },
                                    "required": ["name", "filename", "content"],
                                },
                            },
                            "body": {"type": "string"},
                            "timeout_seconds": {"type": "integer"},
                        },
                        "required": ["method", "url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell_command",
                    "description": "Run a local shell command for recon or exploitation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "cwd": {"type": "string"},
                            "timeout_seconds": {"type": "integer"},
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python_snippet",
                    "description": "Execute a short Python snippet for payload crafting or parsing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "timeout_seconds": {"type": "integer"},
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "webshell_exec",
                    "description": "Execute a command through an existing webshell endpoint with a command parameter.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "command": {"type": "string"},
                            "method": {"type": "string"},
                            "param_name": {"type": "string"},
                            "headers": {"type": "object", "additionalProperties": {"type": "string"}},
                            "params": {"type": "object", "additionalProperties": {"type": "string"}},
                            "timeout_seconds": {"type": "integer"},
                            "expect_marker": {"type": "string"},
                        },
                        "required": ["url", "command"],
                    },
                },
            },
        ]

    def extract_flags(self, text: str) -> list[str]:
        seen: set[str] = set()
        results: list[str] = []
        for match in re.findall(r"flag\{[^}\n]+\}", text, flags=re.IGNORECASE):
            if match not in seen:
                seen.add(match)
                results.append(match)
        return results

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "check_tool_inventory":
            return await self.check_tool_inventory()
        if tool_name == "http_request":
            return await self.http_request(**arguments)
        if tool_name == "run_shell_command":
            return await self.run_shell_command(**arguments)
        if tool_name == "run_python_snippet":
            return await self.run_python_snippet(**arguments)
        if tool_name == "webshell_exec":
            return await self.webshell_exec(**arguments)
        raise ValueError(f"Unknown tool: {tool_name}")

    async def check_tool_inventory(self) -> dict[str, Any]:
        inventory = default_tool_inventory()
        return {
            "tools": [
                {
                    "name": item.name,
                    "category": item.category,
                    "required_for": list(item.required_for),
                    "available": item.available,
                    "install_hint": item.install_hint,
                }
                for item in inventory
            ]
        }

    async def http_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        files: list[dict[str, str]] | None = None,
        body: str | None = None,
        timeout_seconds: int = 20,
    ) -> dict[str, Any]:
        prepared_files = None
        if files:
            prepared_files = []
            for item in files:
                name = str(item.get("name") or "").strip()
                filename = str(item.get("filename") or "").strip()
                content = str(item.get("content") or "")
                content_type = str(item.get("content_type") or "").strip() or None
                if not name or not filename:
                    continue
                file_tuple = (filename, content.encode("utf-8"), content_type) if content_type else (filename, content.encode("utf-8"))
                prepared_files.append((name, file_tuple))
        try:
            async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=timeout_seconds) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    cookies=cookies,
                    data=form,
                    files=prepared_files,
                    content=body.encode("utf-8") if body is not None else None,
                )
        except Exception as exc:  # noqa: BLE001
            name = type(exc).__name__
            message = str(exc).strip()
            raise RuntimeError(f"{name}: {message}" if message else name) from exc
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": self._trim_text(response.text),
        }

    async def webshell_exec(
        self,
        url: str,
        command: str,
        method: str = "GET",
        param_name: str = "cmd",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout_seconds: int = 20,
        expect_marker: str | None = None,
    ) -> dict[str, Any]:
        base = dict(params or {})
        request_method = method.upper()
        if request_method == "GET":
            response = await self.http_request(
                request_method,
                url,
                headers=headers,
                params={**base, param_name: command},
                timeout_seconds=timeout_seconds,
            )
        elif request_method == "POST":
            response = await self.http_request(
                request_method,
                url,
                headers=headers,
                form={**base, param_name: command},
                timeout_seconds=timeout_seconds,
            )
        else:
            raise RuntimeError(f"unsupported webshell method: {method}")
        text = str(response.get("text") or "")
        return {
            **response,
            "marker_found": bool(expect_marker and expect_marker in text),
            "executed_command": command,
            "param_name": param_name,
        }

    async def run_shell_command(
        self,
        command: str,
        cwd: str | None = None,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        parts = shlex.split(command)
        command = self._prefer_uv_command(parts, command)
        parts = shlex.split(command)
        if parts and shutil.which(parts[0]) is None:
            fallback = await self._fallback_shell_command(parts)
            if fallback is not None:
                fallback["fallback_used"] = True
                fallback["original_command"] = command
                return fallback

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._tool_env(),
            start_new_session=True,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            self._kill_process_group(process)
            with contextlib.suppress(Exception):
                await process.communicate()
            return {"exit_code": -1, "stdout": "", "stderr": "command timed out"}
        except asyncio.CancelledError:
            self._kill_process_group(process)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(process.communicate(), timeout=1)
            raise

        return {
            "exit_code": process.returncode,
            "stdout": self._trim_text(stdout.decode("utf-8", errors="replace")),
            "stderr": self._trim_text(stderr.decode("utf-8", errors="replace")),
        }

    async def run_python_snippet(self, code: str, timeout_seconds: int = 30) -> dict[str, Any]:
        snippets_dir = self.runtime_dir / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            prefix="snippet-",
            dir=snippets_dir,
            encoding="utf-8",
            delete=False,
        ) as handle:
            handle.write(code)
            script_path = Path(handle.name)

        return await self.run_shell_command(
            f"{self._python_runner()} {script_path}",
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def _trim_text(text: str, limit: int = 12000) -> str:
        return text[:limit]

    async def _fallback_shell_command(self, parts: list[str]) -> dict[str, Any] | None:
        tool = parts[0]

        if tool == "curl":
            url = next((item for item in parts[1:] if item.startswith("http")), None)
            if url:
                result = await self.http_request("GET", url)
                return {"stdout": json.dumps(result, ensure_ascii=False), "stderr": "", "exit_code": 0}

        if tool in {"httpx", "whatweb"}:
            url = next((item for item in reversed(parts[1:]) if item.startswith("http")), None)
            if url:
                result = await self.http_request("GET", url)
                return {"stdout": json.dumps(result, ensure_ascii=False), "stderr": "", "exit_code": 0}

        if tool == "ffuf":
            if "-u" in parts:
                index = parts.index("-u")
                if index + 1 < len(parts):
                    template = parts[index + 1]
                    common = ["admin", "login", "api", "robots.txt"]
                    findings = []
                    for word in common:
                        url = template.replace("FUZZ", word)
                        response = await self.http_request("GET", url)
                        findings.append({"path": word, "status_code": response["status_code"], "url": url})
                    return {"stdout": json.dumps({"findings": findings}, ensure_ascii=False), "stderr": "", "exit_code": 0}

        if tool == "nmap":
            host = next((item for item in reversed(parts[1:]) if not item.startswith("-")), None)
            if host:
                scan = await self._fallback_port_scan(host)
                return {"stdout": json.dumps(scan, ensure_ascii=False), "stderr": "", "exit_code": 0}

        return None

    async def _fallback_port_scan(self, host: str) -> dict[str, Any]:
        ports = [22, 80, 443, 8080, 3306, 6379]
        results = []
        for port in ports:
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.0)
                writer.close()
                await writer.wait_closed()
                results.append({"port": port, "state": "open"})
            except Exception:
                results.append({"port": port, "state": "closed"})
        return {"host": host, "ports": results}

    @staticmethod
    def _python_runner() -> str:
        if shutil.which("uv") is not None:
            return "uv run python"
        return "python3"

    @staticmethod
    def _prefer_uv_command(parts: list[str], original_command: str) -> str:
        if not parts or parts[0] == "uv" or shutil.which("uv") is None:
            return original_command

        if parts[0] in {"python", "python3"}:
            return shlex.join(["uv", "run", "python", *parts[1:]])

        if parts[0] == "pytest":
            return shlex.join(["uv", "run", *parts])

        return original_command

    def _tool_env(self) -> dict[str, str]:
        env = os.environ.copy()
        preferred = [
            str(self.managed_bin_dir),
            str(Path.home() / ".local" / "bin"),
            "/usr/local/bin",
        ]
        current_path = env.get("PATH", "")
        env["PATH"] = ":".join([*preferred, current_path] if current_path else preferred)
        return env

    @staticmethod
    def _kill_process_group(process: asyncio.subprocess.Process) -> None:
        pid = getattr(process, "pid", None)
        if pid:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
            return
        with contextlib.suppress(ProcessLookupError):
            process.kill()
