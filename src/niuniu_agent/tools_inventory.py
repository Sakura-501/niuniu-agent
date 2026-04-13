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
    search_paths = [
        None,
        str(Path.home() / ".local" / "bin"),
        "/usr/local/bin",
    ]
    for path in search_paths:
        found = shutil.which(name, path=path) if path is not None else shutil.which(name)
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
        ("pip-audit", "supply-chain", ("track2",), "python3 -m pip install --user pip-audit"),
        ("osv-scanner", "supply-chain", ("track2",), "go install github.com/google/osv-scanner/cmd/osv-scanner@latest"),
        ("syft", "supply-chain", ("track2",), "go install github.com/anchore/syft/cmd/syft@latest"),
        ("grype", "supply-chain", ("track2",), "go install github.com/anchore/grype@latest"),
        ("trivy", "supply-chain", ("track2",), "install trivy from official packages or GitHub releases"),
        ("openssl", "crypto", ("all",), "sudo apt-get install -y openssl"),
        ("cloudfox", "cloud", ("track2",), "brew install cloudfox or go install github.com/BishopFox/cloudfox@latest"),
        ("chisel", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install chisel"),
        ("frpc", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install frp"),
        ("frps", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install frp"),
        ("stowaway_admin", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install stowaway"),
        ("stowaway_agent", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install stowaway"),
        ("redis-cli", "service", ("track2", "track3"), "sudo apt-get install -y redis-tools"),
        ("mysql", "service", ("track2", "track3"), "sudo apt-get install -y mysql-client"),
        ("psql", "service", ("track2", "track3"), "sudo apt-get install -y postgresql-client"),
        ("socat", "service", ("track2", "track3"), "sudo apt-get install -y socat"),
        ("proxychains4", "pivot", ("track3", "track4"), "sudo apt-get install -y proxychains4"),
        ("sshuttle", "pivot", ("track3", "track4"), "sudo apt-get install -y sshuttle"),
        ("ligolo-proxy", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install ligolo-ng"),
        ("ligolo-agent", "pivot", ("track3", "track4"), "python3 scripts/fetch_portable_tools.py install ligolo-ng"),
        ("smbclient", "domain", ("track4",), "sudo apt-get install -y smbclient"),
        ("smbmap", "domain", ("track4",), "python3 -m pip install --user smbmap"),
        ("ldapsearch", "domain", ("track4",), "sudo apt-get install -y ldap-utils"),
        ("certipy-ad", "domain", ("track4",), "python3 -m pip install --user certipy-ad and expose it as certipy-ad/certipy"),
        ("petitpotam", "domain", ("track4",), "bundled wrapper under tools/bin/petitpotam"),
        ("dfscoerce", "domain", ("track4",), "bundled wrapper under tools/bin/dfscoerce"),
        ("passthecert", "domain", ("track4",), "bundled wrapper under tools/bin/passthecert"),
        ("powermad-asset", "domain", ("track4",), "bundled Windows PowerShell asset path wrapper under tools/bin/powermad-asset"),
        ("privesccheck-asset", "privesc", ("track4",), "bundled Windows PowerShell asset path wrapper under tools/bin/privesccheck-asset"),
        ("certify-asset", "domain", ("track4",), "bundled Windows AD CS asset path wrapper under tools/bin/certify-asset"),
        ("ms14-068-asset", "domain", ("track4",), "bundled legacy Kerberos asset path wrapper under tools/bin/ms14-068-asset"),
        ("enum4linux-ng", "domain", ("track4",), "git clone https://github.com/cddmp/enum4linux-ng and use enum4linux-ng.py"),
        ("responder", "domain", ("track4",), "git clone https://github.com/SpiderLabs/Responder and expose Responder.py as responder"),
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
        ("winpeasx64", "privesc", ("track4",), "python3 scripts/fetch_portable_tools.py install winpeas"),
        ("msfconsole", "framework", ("track2", "track3", "track4"), "brew install metasploit or install metasploit-framework from official packages"),
        ("php", "service", ("track1", "track3"), "sudo apt-get install -y php-cli"),
        ("tcpdump", "service", ("track3", "track4"), "sudo apt-get install -y tcpdump"),
        ("tmux", "base", ("track3", "track4"), "sudo apt-get install -y tmux"),
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
