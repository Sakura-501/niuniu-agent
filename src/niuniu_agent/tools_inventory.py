from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ToolAvailability:
    name: str
    category: str
    required_for: tuple[str, ...]
    available: bool
    install_hint: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tool_path(name: str) -> str | None:
    found = shutil.which(name)
    if found is not None:
        return found
    managed = _repo_root() / "tools" / "bin" / name
    if managed.exists() and managed.is_file():
        return str(managed)
    return None


def default_tool_inventory() -> list[ToolAvailability]:
    specs = [
        ("python3", "base", ("all",), "sudo apt-get install -y python3 python3-pip python3.12-venv"),
        ("pip3", "base", ("all",), "sudo apt-get install -y python3-pip"),
        ("uv", "base", ("all",), "python3 -m pip install --user uv"),
        ("curl", "base", ("all",), "sudo apt-get install -y curl"),
        ("jq", "base", ("all",), "sudo apt-get install -y jq"),
        ("rg", "base", ("all",), "sudo apt-get install -y ripgrep"),
        ("nc", "base", ("all",), "sudo apt-get install -y netcat-openbsd"),
        ("dig", "base", ("all",), "sudo apt-get install -y dnsutils"),
        ("ffuf", "web", ("track1",), "sudo apt-get install -y ffuf"),
        ("feroxbuster", "web", ("track1",), "cargo install feroxbuster or install the official Linux binary from GitHub releases"),
        ("gobuster", "web", ("track1",), "sudo apt-get install -y gobuster"),
        ("rustscan", "service", ("track1", "track2", "track3", "track4"), "brew install rustscan or cargo install rustscan"),
        ("nikto", "web", ("track1",), "sudo apt-get install -y nikto"),
        ("nmap", "service", ("track1", "track2", "track3", "track4"), "sudo apt-get install -y nmap"),
        ("masscan", "service", ("track2", "track3", "track4"), "sudo apt-get install -y masscan"),
        ("whatweb", "web", ("track1", "track2"), "sudo apt-get install -y whatweb"),
        ("sqlmap", "web", ("track1", "track2"), "sudo apt-get install -y sqlmap"),
        ("nuclei", "cve", ("track2",), "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"),
        ("fscan", "cve", ("track2", "track3", "track4"), "python3 scripts/fetch_portable_tools.py install fscan"),
        ("httpx", "cve", ("track2",), "go install github.com/projectdiscovery/httpx/cmd/httpx@latest"),
        ("openssl", "crypto", ("all",), "sudo apt-get install -y openssl"),
        ("cloudfox", "cloud", ("track2",), "brew install cloudfox or go install github.com/BishopFox/cloudfox@latest"),
        ("frpc", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install frp"),
        ("frps", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install frp"),
        ("stowaway_admin", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install stowaway"),
        ("stowaway_agent", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install stowaway"),
        ("redis-cli", "service", ("track2", "track3"), "sudo apt-get install -y redis-tools"),
        ("mysql", "service", ("track2", "track3"), "sudo apt-get install -y mysql-client"),
        ("psql", "service", ("track2", "track3"), "sudo apt-get install -y postgresql-client"),
        ("socat", "service", ("track2", "track3"), "sudo apt-get install -y socat"),
        ("proxychains4", "pivot", ("track3", "track4"), "sudo apt-get install -y proxychains4"),
        ("smbclient", "domain", ("track4",), "sudo apt-get install -y smbclient"),
        ("ldapsearch", "domain", ("track4",), "sudo apt-get install -y ldap-utils"),
        ("hydra", "domain", ("track3", "track4"), "sudo apt-get install -y hydra"),
        ("john", "domain", ("track3", "track4"), "sudo apt-get install -y john"),
        ("hashcat", "domain", ("track3", "track4"), "sudo apt-get install -y hashcat"),
        ("impacket-secretsdump", "domain", ("track4",), "python3 -m pip install --user impacket"),
        ("impacket-psexec", "domain", ("track4",), "python3 -m pip install --user impacket"),
        ("impacket-wmiexec", "domain", ("track4",), "python3 -m pip install --user impacket"),
        ("bloodhound-python", "domain", ("track4",), "python3 -m pip install --user bloodhound"),
        ("kerbrute", "domain", ("track4",), "go install github.com/ropnop/kerbrute@latest"),
        ("netexec", "domain", ("track4",), "python3 -m pip install --user netexec"),
        ("linpeas", "privesc", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install linpeas"),
        ("pspy", "privesc", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install pspy"),
        ("msfconsole", "framework", ("track2", "track3", "track4"), "brew install metasploit or install metasploit-framework from official packages"),
    ]
    return [
        ToolAvailability(
            name=name,
            category=category,
            required_for=required_for,
            available=tool_path(name) is not None,
            install_hint=hint,
        )
        for name, category, required_for, hint in specs
    ]
