from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolAvailability:
    name: str
    category: str
    required_for: tuple[str, ...]
    available: bool
    install_hint: str


def default_tool_inventory() -> list[ToolAvailability]:
    specs = [
        ("python3", "base", ("all",), "sudo apt-get install -y python3 python3-pip python3.12-venv"),
        ("curl", "base", ("all",), "sudo apt-get install -y curl"),
        ("jq", "base", ("all",), "sudo apt-get install -y jq"),
        ("rg", "base", ("all",), "sudo apt-get install -y ripgrep"),
        ("ffuf", "web", ("track1",), "sudo apt-get install -y ffuf"),
        ("nmap", "service", ("track1", "track2", "track3", "track4"), "sudo apt-get install -y nmap"),
        ("whatweb", "web", ("track1", "track2"), "sudo apt-get install -y whatweb"),
        ("sqlmap", "web", ("track1", "track2"), "sudo apt-get install -y sqlmap"),
        ("nuclei", "cve", ("track2",), "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"),
        ("httpx", "cve", ("track2",), "go install github.com/projectdiscovery/httpx/cmd/httpx@latest"),
        ("openssl", "crypto", ("all",), "sudo apt-get install -y openssl"),
        ("smbclient", "domain", ("track4",), "sudo apt-get install -y smbclient"),
        ("ldapsearch", "domain", ("track4",), "sudo apt-get install -y ldap-utils"),
        ("impacket-secretsdump", "domain", ("track4",), "python -m pip install impacket"),
    ]
    return [
        ToolAvailability(
            name=name,
            category=category,
            required_for=required_for,
            available=shutil.which(name) is not None,
            install_hint=hint,
        )
        for name, category, required_for, hint in specs
    ]
