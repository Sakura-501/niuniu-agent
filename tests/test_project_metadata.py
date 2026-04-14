from pathlib import Path
import tomllib


def test_pyproject_declares_tools_extra_for_python_tooling() -> None:
    pyproject = Path("/Users/nonoge/Desktop/auto_pentest/niuniu-agent/pyproject.toml")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    optional = data["project"]["optional-dependencies"]
    tools = optional["tools"]

    assert any(item.startswith("impacket") for item in tools)
    assert any(item.startswith("certipy-ad") for item in tools)
    assert any(item.startswith("smbmap") for item in tools)
    assert any(item.startswith("pip-audit") for item in tools)
    assert any(item.startswith("bloodhound @ git+") for item in tools)
    assert any(item.startswith("netexec @ git+") for item in tools)
