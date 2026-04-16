from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class CapabilitySkill:
    name: str
    description: str
    trigger_keywords: tuple[str, ...]
    usage_guidance: str
    recommended_tracks: tuple[str, ...]
    path: Path
    body: str


@dataclass(frozen=True, slots=True)
class SkillBehavior:
    trigger_keywords: tuple[str, ...]
    usage_guidance: str
    recommended_tracks: tuple[str, ...] = ()


SKILL_BEHAVIORS: dict[str, SkillBehavior] = {
    "web-surface-mapping": SkillBehavior(
        trigger_keywords=("web", "portal", "site", "login", "admin", "dashboard", "http"),
        usage_guidance="Start with route discovery, parameter discovery, and framework clues before deeper testing.",
        recommended_tracks=("track1", "track2"),
    ),
    "service-enumeration": SkillBehavior(
        trigger_keywords=("service", "port", "tcp", "udp", "ssh", "redis", "mysql", "fastapi"),
        usage_guidance="Enumerate ports, protocols, banners, and reachable services before choosing exploit tools.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "port-scan-operations": SkillBehavior(
        trigger_keywords=("rustscan", "nmap", "masscan", "port scan", "tcp", "udp", "banner"),
        usage_guidance="Use fast discovery first, then confirm with service fingerprinting before exploitation.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "pearcmd-php-shell-drop": SkillBehavior(
        trigger_keywords=("pearcmd", "lfi", "php shell", "config-create", "pear"),
        usage_guidance="Use this when PHP LFI already exists and PEAR offers the shortest path to a writable shell file.",
        recommended_tracks=("track3", "track4"),
    ),
    "redis-mariadb-lateral-movement": SkillBehavior(
        trigger_keywords=("redis", "mariadb", "mysql", "postgres", "internal db", "6379", "3306", "5432"),
        usage_guidance="Use this when internal Redis or database services become visible from a foothold and you need a focused next-step workflow.",
        recommended_tracks=("track3", "track4"),
    ),
    "php-session-hijack-helper": SkillBehavior(
        trigger_keywords=("php session", "sess_", "csrf", "admin session", "/tmp/sess"),
        usage_guidance="Use this when PHP session files are readable and you need to recover admin or CSRF state quickly.",
        recommended_tracks=("track3", "track4"),
    ),
    "tool-flask-session-cookie-manager": SkillBehavior(
        trigger_keywords=("flask session", "flask cookie", "session cookie", "itsdangerous", "secret_key", "securecookie"),
        usage_guidance="Load this skill when Flask signed session cookies are in play and you need concrete decode or re-sign steps.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "proxy-php-ssrf-lfi-helper": SkillBehavior(
        trigger_keywords=("proxy.php", "ssrf", "file://", "lfi", "internal http"),
        usage_guidance="Use this when a proxy.php-style fetch primitive needs fast SSRF/LFI target generation.",
        recommended_tracks=("track3", "track4"),
    ),
    "known-vulnerability-mapping": SkillBehavior(
        trigger_keywords=("cve", "version", "apache", "nginx", "spring", "grafana", "fastapi"),
        usage_guidance="Normalize product and version clues, then rank likely known-vulnerability paths by fit.",
        recommended_tracks=("track2",),
    ),
    "cve-template-scanning": SkillBehavior(
        trigger_keywords=("nuclei", "fscan", "cve", "template", "fingerprint", "httpx"),
        usage_guidance="Run scoped template validation only after fingerprinting supports a likely known-vulnerability path.",
        recommended_tracks=("track2",),
    ),
    "web-vulnerability-testing": SkillBehavior(
        trigger_keywords=("sqli", "xss", "upload", "ssti", "idor", "auth", "template"),
        usage_guidance="Exploit only after reconnaissance confirms a likely path, and keep the winning request reproducible.",
        recommended_tracks=("track1", "track2"),
    ),
    "pentest-entrypoint-triage": SkillBehavior(
        trigger_keywords=("entrypoint", "ip only", "url only", "target ip", "first pass", "initial triage", "http", "https"),
        usage_guidance="Start with a fast first-pass triage to choose one exploit lane before broad scanning.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "web-foothold-chain-playbook": SkillBehavior(
        trigger_keywords=("webshell", "upload bypass", "lfi", "ssrf", "sqli", "outfile", "foothold chain", "rce"),
        usage_guidance="Use a deterministic web exploit chain to convert a web bug into file-read or code execution.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "internal-pivot-flow": SkillBehavior(
        trigger_keywords=("internal segment", "pivot flow", "next hop", "reachable ip", "route table", "arp", "foothold"),
        usage_guidance="Map the current foothold and next-hop network path before choosing a pivot tool or internal exploit.",
        recommended_tracks=("track3", "track4"),
    ),
    "credential-secret-hunting": SkillBehavior(
        trigger_keywords=("secret", "credential", "password", "token", "session", "config leak", "redis key", "db credential"),
        usage_guidance="Search configs, sessions, caches, and databases before brute force or random lateral movement.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "flag-discovery-and-submission": SkillBehavior(
        trigger_keywords=("flag", "flag search", "submit flag", "multi-flag", "local flag"),
        usage_guidance="Use an ordered flag-search workflow once any foothold or file-read primitive exists.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "ad-internal-compromise-flow": SkillBehavior(
        trigger_keywords=("domain", "ad", "kerberos", "ldap", "smb", "dc", "adcs", "winrm"),
        usage_guidance="Use a low-noise AD compromise workflow built around validated identity evidence.",
        recommended_tracks=("track4",),
    ),
    "web-content-discovery": SkillBehavior(
        trigger_keywords=("ffuf", "gobuster", "feroxbuster", "dir", "vhost", "content discovery", "route"),
        usage_guidance="Use narrow wordlists and filters first, then recurse only where the signal justifies the load.",
        recommended_tracks=("track1", "track2"),
    ),
    "api-workflow-testing": SkillBehavior(
        trigger_keywords=("api", "json", "token", "jwt", "graphql", "rest"),
        usage_guidance="Prefer structured request/response diffing, auth flow checks, and minimal payload mutations.",
        recommended_tracks=("track1", "track2"),
    ),
    "supply-chain-poisoning-assessment": SkillBehavior(
        trigger_keywords=("supply chain", "dependency confusion", "package poisoning", "requirements.txt", "package.json", "workflow", "registry", "pip", "npm"),
        usage_guidance="Start from manifests, registry trust, and CI workflow boundaries before looking for runtime sinks.",
        recommended_tracks=("track2",),
    ),
    "dependency-confusion-assessment": SkillBehavior(
        trigger_keywords=("dependency confusion", "private package", "private registry", "pip index", "npm scope", "package name collision"),
        usage_guidance="Map resolver precedence, internal names, and install-time execution paths before testing runtime behavior.",
        recommended_tracks=("track2",),
    ),
    "ci-workflow-poisoning": SkillBehavior(
        trigger_keywords=("github actions", "gitlab ci", "jenkinsfile", "workflow poisoning", "uses:", "artifact", "action pin"),
        usage_guidance="Treat CI configuration as the primary attack surface and check pins, scripts, and artifact trust first.",
        recommended_tracks=("track2", "track3"),
    ),
    "cloud-asset-assessment": SkillBehavior(
        trigger_keywords=("cloud", "bucket", "metadata", "ai", "model", "inference", "llm"),
        usage_guidance="Check metadata, object storage, model-serving APIs, and exposed infrastructure control points.",
        recommended_tracks=("track2",),
    ),
    "ai-platform-attack-surface": SkillBehavior(
        trigger_keywords=("dify", "gradio", "open-webui", "langflow", "flowise", "ragflow", "llm portal", "ai platform", "model ui"),
        usage_guidance="Fingerprint the AI platform first, then map the frontend-to-backend trust boundary before attempting exploit paths.",
        recommended_tracks=("track2",),
    ),
    "dify-self-hosted-assessment": SkillBehavior(
        trigger_keywords=("dify", "127.0.0.1:5001", "/console/api", "/install", "/init", "serverreference", "createServerReference"),
        usage_guidance="Treat Dify as a Next.js frontend with internal console/public APIs and look for same-origin bridges to loopback services.",
        recommended_tracks=("track2",),
    ),
    "gradio-api-abuse": SkillBehavior(
        trigger_keywords=("gradio", "/config", "fn_index", "api_name", "/run/predict", "session_hash", "/file="),
        usage_guidance="Work from /config and backend function mapping, then exercise stateful Gradio API paths directly instead of broad fuzzing.",
        recommended_tracks=("track2",),
    ),
    "nextjs-middleware-bypass": SkillBehavior(
        trigger_keywords=("next.js", "nextjs", "middleware", "x-middleware-subrequest", "server action", "createServerReference"),
        usage_guidance="Use concrete Next.js middleware bypass checks before assuming the auth boundary is solid.",
        recommended_tracks=("track2",),
    ),
    "local-exp-catalog": SkillBehavior(
        trigger_keywords=("exp", "poc", "exploit", "/root/niuniu-agent/exp", "local exploit", "cve"),
        usage_guidance="Check the local EXP catalog before external research when a product or CVE hint already exists.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "cloud-security-enumeration": SkillBehavior(
        trigger_keywords=("cloudfox", "cloudsword", "bucket", "metadata", "iam", "aksk", "object storage"),
        usage_guidance="Map cloud identities, metadata, storage, and public management surfaces before exploitation.",
        recommended_tracks=("track2",),
    ),
    "lateral-movement-planning": SkillBehavior(
        trigger_keywords=("pivot", "lateral", "internal", "foothold", "next hop"),
        usage_guidance="Track the current foothold, next reachable asset, and the least wasteful pivot option.",
        recommended_tracks=("track3", "track4"),
    ),
    "tunnel-and-pivot-operations": SkillBehavior(
        trigger_keywords=("frp", "stowaway", "pivot", "socks", "tunnel", "proxychains", "reverse shell"),
        usage_guidance="Choose the minimum stable tunnel that enables the next step, and record cleanup details.",
        recommended_tracks=("track3", "track4"),
    ),
    "privilege-path-analysis": SkillBehavior(
        trigger_keywords=("privesc", "sudo", "capability", "credential", "persistence"),
        usage_guidance="Enumerate privilege paths, reusable credentials, and long-lived access opportunities.",
        recommended_tracks=("track3", "track4"),
    ),
    "persistence-operations": SkillBehavior(
        trigger_keywords=("persistence", "callback", "beacon", "frp", "stowaway", "listener"),
        usage_guidance="Preserve only the access that is necessary for the next phase, and keep cleanup explicit.",
        recommended_tracks=("track3", "track4"),
    ),
    "linux-privilege-escalation": SkillBehavior(
        trigger_keywords=("linpeas", "pspy", "sudo -l", "capability", "linux privesc", "cron"),
        usage_guidance="Run a ranked Linux privesc workflow instead of broad repetitive local checks.",
        recommended_tracks=("track3", "track4"),
    ),
    "directory-identity-enumeration": SkillBehavior(
        trigger_keywords=("domain", "ad", "ldap", "kerberos", "dc", "smb"),
        usage_guidance="Map identity infrastructure, core hosts, trust edges, and the shortest path to privileged access.",
        recommended_tracks=("track4",),
    ),
    "domain-operations": SkillBehavior(
        trigger_keywords=("impacket", "bloodhound", "kerbrute", "netexec", "mimikatz", "winrm", "adcs"),
        usage_guidance="Validate credentials carefully, then collect only the domain graph edges or secrets needed for the next move.",
        recommended_tracks=("track4",),
    ),
    "evidence-capture": SkillBehavior(
        trigger_keywords=("flag", "submit", "retry", "recovery"),
        usage_guidance="Capture the minimal evidence set, submit valuable artifacts immediately, and use feedback to branch cleanly.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "resource-aware-execution": SkillBehavior(
        trigger_keywords=("memory", "resource", "threads", "rate", "concurrency", "scan budget"),
        usage_guidance="Constrain heavy tools explicitly and kill stale jobs that stop producing signal.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "ctf-core-knowledge": SkillBehavior(
        trigger_keywords=("ctf", "flag", "sqli", "ssti", "idor", "xss", "ssrf", "lfi", "jwt", "default credentials"),
        usage_guidance="Load this skill when the problem is mainly about recognizing the vulnerability family and the shortest common CTF path to the flag.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
    "tool-rustscan-nmap": SkillBehavior(
        trigger_keywords=("rustscan", "nmap", "masscan", "portscan"),
        usage_guidance="Load this skill when you need concrete rustscan/nmap operator steps instead of generic recon guidance.",
    ),
    "tool-ffuf-gobuster": SkillBehavior(
        trigger_keywords=("ffuf", "gobuster", "feroxbuster", "dirsearch"),
        usage_guidance="Load this skill when you need concrete content-discovery tactics and safe filters.",
    ),
    "tool-nuclei-fscan": SkillBehavior(
        trigger_keywords=("nuclei", "fscan", "template scan", "cve scan"),
        usage_guidance="Load this skill when you need concrete nuclei/fscan usage patterns and scoped CVE validation.",
    ),
    "tool-cloudfox": SkillBehavior(
        trigger_keywords=("cloudfox", "cloud enum", "iam enum"),
        usage_guidance="Load this skill when cloudfox is the likely next tool and you need practical cloud enumeration steps.",
    ),
    "tool-frp-stowaway": SkillBehavior(
        trigger_keywords=("frp", "stowaway", "pivot tool", "reverse tunnel"),
        usage_guidance="Load this skill when you need concrete tunnel or multi-hop pivot usage.",
    ),
    "tool-impacket-netexec-bloodhound": SkillBehavior(
        trigger_keywords=("impacket", "netexec", "bloodhound", "kerbrute"),
        usage_guidance="Load this skill when you need a concrete AD tool workflow.",
    ),
    "tool-linpeas-pspy": SkillBehavior(
        trigger_keywords=("linpeas", "pspy", "linux privesc tool"),
        usage_guidance="Load this skill when you need concrete Linux local escalation tooling steps.",
    ),
    "tool-metasploit": SkillBehavior(
        trigger_keywords=("metasploit", "msfconsole", "meterpreter"),
        usage_guidance="Load this skill when Metasploit becomes the most practical exploit or handler path.",
    ),
    "tool-mimikatz-windows": SkillBehavior(
        trigger_keywords=("mimikatz", "sekurlsa", "windows creds"),
        usage_guidance="Load this skill when you need to stage or reason about a Windows-only mimikatz workflow.",
    ),
    "tool-sqlmap-whatweb-nikto": SkillBehavior(
        trigger_keywords=("sqlmap", "whatweb", "nikto"),
        usage_guidance="Load this skill when you need concrete fingerprinting and SQLi triage steps for internal web targets.",
    ),
    "tool-socat-proxychains": SkillBehavior(
        trigger_keywords=("socat", "proxychains", "relay", "socks"),
        usage_guidance="Load this skill when you need lightweight relays or proxied follow-on tooling.",
    ),
    "tool-kerbrute-smb-enum": SkillBehavior(
        trigger_keywords=("kerbrute", "smbmap", "enum4linux", "responder"),
        usage_guidance="Load this skill when you need concrete SMB and identity enumeration steps.",
    ),
    "tool-feroxbuster-masscan": SkillBehavior(
        trigger_keywords=("feroxbuster", "masscan"),
        usage_guidance="Load this skill when you need heavier recursive content or high-rate range discovery.",
    ),
    "tool-certipy-adcs": SkillBehavior(
        trigger_keywords=("certipy", "adcs", "esc"),
        usage_guidance="Load this skill when AD CS or certificate abuse becomes relevant.",
    ),
    "tool-petitpotam-dfscoerce": SkillBehavior(
        trigger_keywords=("petitpotam", "dfscoerce", "coerce", "efsrpc", "dfsnm", "ntlm relay", "forced auth"),
        usage_guidance="Load this skill when you need concrete coercion and forced-authentication steps against Windows/AD targets.",
    ),
    "tool-passthecert": SkillBehavior(
        trigger_keywords=("passthecert", "schannel", "ldap certificate", "pkinit", "certificate auth", "cert auth"),
        usage_guidance="Load this skill when certificate auth is available but PKINIT is missing or LDAP Schannel is the practical path.",
    ),
    "tool-nopac": SkillBehavior(
        trigger_keywords=("nopac", "cve-2021-42278", "cve-2021-42287", "sam-the-admin", "machineaccountquota", "s4u2self"),
        usage_guidance="Load this skill when the noPac machine-account rename chain is relevant and you need concrete scanner or exploit steps.",
    ),
    "tool-ajpy-tomcat": SkillBehavior(
        trigger_keywords=("ajpy", "ajp", "ghostcat", "cve-2020-1938", "tomcat ajp", "war upload"),
        usage_guidance="Load this skill when Tomcat AJP exposure or Ghostcat-style file-read/upload paths are in play.",
    ),
    "tool-openssh-regresshion": SkillBehavior(
        trigger_keywords=("openssh", "sshd", "regresshion", "cve-2024-6387", "login grace time", "signal handler race", "ssh banner"),
        usage_guidance="Load this skill when OpenSSH banners or version clues suggest regreSSHion and you need the local scanner/exploit helper workflow.",
    ),
    "tool-phpggc": SkillBehavior(
        trigger_keywords=("phpggc", "php unserialize", "phar", "gadget chain", "deserialization php"),
        usage_guidance="Load this skill when a PHP deserialization sink exists and you need a gadget-chain generator quickly.",
    ),
    "tool-neoreg": SkillBehavior(
        trigger_keywords=("neoreg", "neo-regeorg", "regeorg", "tunnel.php", "webshell tunnel", "socks via webshell"),
        usage_guidance="Load this skill when you need a webshell-backed SOCKS or port-forward tunnel via Neo-reGeorg.",
    ),
    "tool-suo5-forward-proxy": SkillBehavior(
        trigger_keywords=("suo5", "forward proxy", "http tunnel", "socks5 tunnel", "suo5.jsp", "suo5.php"),
        usage_guidance="Load this skill when you need a high-performance forward proxy or tunnel through an uploaded suo5 server asset.",
    ),
    "tool-jsfinder": SkillBehavior(
        trigger_keywords=("jsfinder", "js routes", "extract urls from js", "subdomain from js", "javascript endpoints"),
        usage_guidance="Load this skill when you need to mine URLs, routes, APIs, or subdomains from JavaScript assets quickly.",
    ),
    "tool-rogue-service-exploits": SkillBehavior(
        trigger_keywords=("redis rogue", "redis module", "rogue mysql", "grafanaexp", "cve-2021-43798", "grafana file read", "rogue_mysql_server"),
        usage_guidance="Load this skill when the shortest exploit path is a rogue service handshake, Redis module-load path, or Grafana arbitrary file-read workflow.",
    ),
    "tool-windows-ad-stage-assets": SkillBehavior(
        trigger_keywords=("powermad", "privesccheck", "certify", "ms14-068", "machineaccountquota", "adidns", "windows asset", "rubeus", "sharphound", "sweetpotato", "sebackupprivilege"),
        usage_guidance="Load this skill when a Windows foothold needs staged AD or local escalation assets from the operator host.",
    ),
    "tool-chisel": SkillBehavior(
        trigger_keywords=("chisel",),
        usage_guidance="Load this skill when you need a lightweight tunnel or SOCKS pivot path.",
    ),
    "tool-ligolo-sshuttle": SkillBehavior(
        trigger_keywords=("ligolo", "sshuttle"),
        usage_guidance="Load this skill when you need concrete ligolo-ng or sshuttle pivot steps.",
    ),
    "tool-winpeas-windows-assets": SkillBehavior(
        trigger_keywords=("winpeas", "windows asset", "windows privesc"),
        usage_guidance="Load this skill when a Windows foothold needs staged privilege-escalation assets.",
    ),
}


class SkillRegistry:
    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or self.default_skills_dir()
        self.skills = self._load_skills()
        self._available_description_cache = self._build_available_description()

    @staticmethod
    def default_skills_dir() -> Path:
        return Path(__file__).resolve().parents[3] / "skills"

    def _load_skills(self) -> list[CapabilitySkill]:
        if not self.skills_dir.exists():
            return []
        loaded: list[CapabilitySkill] = []
        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            meta, body = self._parse_frontmatter(path.read_text(encoding="utf-8"))
            name = meta.get("name", path.parent.name)
            behavior = SKILL_BEHAVIORS.get(name) or self._default_behavior(meta.get("description", ""), body)
            loaded.append(
                CapabilitySkill(
                    name=name,
                    description=meta.get("description", "No description provided."),
                    trigger_keywords=behavior.trigger_keywords,
                    usage_guidance=behavior.usage_guidance,
                    recommended_tracks=behavior.recommended_tracks,
                    path=path,
                    body=body.strip(),
                )
            )
        return loaded

    @staticmethod
    def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
        if not match:
            return {}, text
        meta: dict[str, str] = {}
        for raw_line in match.group(1).splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
        return meta, match.group(2)

    @staticmethod
    def _default_behavior(description: str, body: str) -> SkillBehavior:
        tokens = []
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", f"{description} {body}".lower()):
            if token not in tokens:
                tokens.append(token)
        return SkillBehavior(
            trigger_keywords=tuple(tokens[:12]),
            usage_guidance="Load the full skill body before acting.",
        )

    def _build_available_description(self) -> str:
        if not self.skills:
            return "(no skills available)"
        return "\n".join(
            f"- {skill.name}: {skill.description}"
            for skill in sorted(self.skills, key=lambda item: item.name)
        )

    def describe_available(self) -> str:
        return self._available_description_cache

    def load_full_text(self, name: str) -> str:
        skill = next((item for item in self.skills if item.name == name), None)
        if skill is None:
            known = ", ".join(sorted(item.name for item in self.skills)) or "(none)"
            return f"Error: Unknown skill '{name}'. Available skills: {known}"
        return f"<skill name=\"{skill.name}\">\n{skill.body}\n</skill>"

    def select_for_text(self, text: str) -> list[CapabilitySkill]:
        haystack = text.lower()
        selected: list[CapabilitySkill] = []
        for skill in self.skills:
            if any(keyword in haystack for keyword in skill.trigger_keywords):
                selected.append(skill)
        return selected

    def select_for_track(self, track: str) -> list[CapabilitySkill]:
        return [skill for skill in self.skills if track in skill.recommended_tracks]

    def select(self, description: str, track: str | None = None) -> list[CapabilitySkill]:
        selected = self.select_for_text(description)
        if track is not None:
            track_skills = self.select_for_track(track)
            merged = {skill.name: skill for skill in (*selected, *track_skills)}
            return list(merged.values())
        return selected
