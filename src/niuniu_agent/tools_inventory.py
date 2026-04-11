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
        ("nc", "base", ("all",), "sudo apt-get install -y netcat-openbsd"),
        ("dig", "base", ("all",), "sudo apt-get install -y dnsutils"),
        ("ffuf", "web", ("track1",), "sudo apt-get install -y ffuf"),
        ("feroxbuster", "web", ("track1",), "cargo install feroxbuster"),
        ("nikto", "web", ("track1",), "sudo apt-get install -y nikto"),
        ("nmap", "service", ("track1", "track2", "track3", "track4"), "sudo apt-get install -y nmap"),
        ("masscan", "service", ("track2", "track3", "track4"), "sudo apt-get install -y masscan"),
        ("whatweb", "web", ("track1", "track2"), "sudo apt-get install -y whatweb"),
        ("sqlmap", "web", ("track1", "track2"), "sudo apt-get install -y sqlmap"),
        ("nuclei", "cve", ("track2",), "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"),
        ("httpx", "cve", ("track2",), "go install github.com/projectdiscovery/httpx/cmd/httpx@latest"),
        ("openssl", "crypto", ("all",), "sudo apt-get install -y openssl"),
        ("redis-cli", "service", ("track2", "track3"), "sudo apt-get install -y redis-tools"),
        ("mysql", "service", ("track2", "track3"), "sudo apt-get install -y mysql-client"),
        ("psql", "service", ("track2", "track3"), "sudo apt-get install -y postgresql-client"),
        ("smbclient", "domain", ("track4",), "sudo apt-get install -y smbclient"),
        ("ldapsearch", "domain", ("track4",), "sudo apt-get install -y ldap-utils"),
        ("hydra", "domain", ("track3", "track4"), "sudo apt-get install -y hydra"),
        ("john", "domain", ("track3", "track4"), "sudo apt-get install -y john"),
        ("hashcat", "domain", ("track3", "track4"), "sudo apt-get install -y hashcat"),
        ("impacket-secretsdump", "domain", ("track4",), "python -m pip install impacket"),
        ("impacket-psexec", "domain", ("track4",), "python -m pip install impacket"),
        ("impacket-wmiexec", "domain", ("track4",), "python -m pip install impacket"),
        ("bloodhound-python", "domain", ("track4",), "python -m pip install bloodhound"),
        ("kerbrute", "domain", ("track4",), "go install github.com/ropnop/kerbrute@latest"),
        ("netexec", "domain", ("track4",), "python -m pip install netexec"),
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
