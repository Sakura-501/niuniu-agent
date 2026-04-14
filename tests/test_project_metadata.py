from pathlib import Path
import tomllib


def test_pyproject_declares_tools_extra_for_python_tooling() -> None:
    pyproject = Path("/Users/nonoge/Desktop/auto_pentest/niuniu-agent/pyproject.toml")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    optional = data["project"]["optional-dependencies"]
    tools = optional["tools"]
    tools_set = set(tools)

    assert any(item.startswith("impacket") for item in tools)
    assert any(item.startswith("certipy-ad") for item in tools)
    assert any(item.startswith("smbmap") for item in tools)
    assert any(item.startswith("pip-audit") for item in tools)
    assert any(item.startswith("bloodhound @ git+") for item in tools)
    assert any(item.startswith("netexec @ git+") for item in tools)
    assert "beautifulsoup4>=4.13.4,<4.14" in tools_set
    assert "blinker==1.9.0" in tools_set
    assert "bs4==0.0.2" in tools_set
    assert "curl-cffi==0.15.0" in tools_set
    assert "flask==3.1.3" in tools_set
    assert "itsdangerous==2.2.0" in tools_set
    assert "jinja2==3.1.6" in tools_set
    assert "markupsafe==3.0.3" in tools_set
    assert "pysocks==1.7.1" in tools_set
    assert "pyspnego==0.12.1" in tools_set
    assert "requests-ntlm==1.3.0" in tools_set
    assert "soupsieve==2.8.3" in tools_set
    assert "werkzeug==3.1.8" in tools_set
