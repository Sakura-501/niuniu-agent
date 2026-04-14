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
        ]

    def extract_flags(self, text: str) -> list[str]:
        seen: set[str] = set()
        results: list[str] = []
        denylist = {
            "flag_count",
            "flag_got_count",
            "submit_flag",
            "last_flag",
            "flag_submitted",
            "persistent_flag_record",
        }
        for match in re.findall(r"flag\{[^}\n]+\}", text, flags=re.IGNORECASE):
            if match not in seen:
                seen.add(match)
                results.append(match)
        for match in re.findall(r"(?<![A-Za-z0-9_])(flag[A-Za-z0-9{}:-]{8,255})(?![A-Za-z0-9_])", text, flags=re.IGNORECASE):
            lowered = match.lower()
            if lowered in denylist:
                continue
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
        body: str | None = None,
        timeout_seconds: int = 20,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=timeout_seconds) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                content=body.encode("utf-8") if body is not None else None,
            )
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": self._trim_text(response.text),
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
