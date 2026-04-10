from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapabilitySkill:
    name: str
    description: str
    trigger_keywords: tuple[str, ...]
    usage_guidance: str
    recommended_tracks: tuple[str, ...]


class SkillRegistry:
    def __init__(self) -> None:
        self.skills = [
            CapabilitySkill(
                "recon_web",
                "Web attack surface discovery for portals, routes, parameters, and static clues.",
                ("web", "portal", "site", "login", "admin", "dashboard", "http"),
                "Start with route discovery, parameter discovery, and tech stack identification before exploitation.",
                ("track1", "track2"),
            ),
            CapabilitySkill(
                "recon_service",
                "Service and protocol discovery for non-pure-web targets.",
                ("service", "port", "tcp", "udp", "ssh", "redis", "mysql", "fastapi"),
                "Enumerate ports, service banners, and versions before choosing exploit paths.",
                ("track1", "track2", "track3", "track4"),
            ),
            CapabilitySkill(
                "cve_mapping",
                "Map versions and fingerprints to likely CVEs.",
                ("cve", "version", "apache", "nginx", "spring", "grafana", "fastapi"),
                "Identify component and version first, then rank likely exploit candidates.",
                ("track2",),
            ),
            CapabilitySkill(
                "exploit_web",
                "Web exploitation for common vuln classes.",
                ("sqli", "xss", "upload", "ssti", "idor", "auth", "template"),
                "Exploit only after reconnaissance confirms a likely path and record exact requests.",
                ("track1", "track2"),
            ),
            CapabilitySkill(
                "exploit_api",
                "JSON/API authn-authz and workflow exploitation.",
                ("api", "json", "token", "jwt", "graphql", "rest"),
                "Prefer structured API reasoning, authentication flow checks, and response diffing.",
                ("track1", "track2"),
            ),
            CapabilitySkill(
                "cloud_ai_surface",
                "Cloud and AI infrastructure discovery.",
                ("cloud", "bucket", "metadata", "ai", "model", "inference", "llm"),
                "Look for metadata endpoints, object storage, model APIs, and infra exposure.",
                ("track2",),
            ),
            CapabilitySkill(
                "pivot_lateral",
                "Multi-step pivot and lateral planning.",
                ("pivot", "lateral", "internal", "foothold", "next hop"),
                "Track current foothold, next reachable segment, and credentials worth reusing.",
                ("track3", "track4"),
            ),
            CapabilitySkill(
                "privesc_maintain",
                "Privilege escalation and persistence planning.",
                ("privesc", "sudo", "capability", "credential", "persistence"),
                "Enumerate privilege paths and capture credentials or long-lived access paths.",
                ("track3", "track4"),
            ),
            CapabilitySkill(
                "domain_enum",
                "Domain and Active Directory enumeration.",
                ("domain", "ad", "ldap", "kerberos", "dc", "smb"),
                "Map domain roles, core hosts, and shortest escalation paths before action.",
                ("track4",),
            ),
            CapabilitySkill(
                "flag_submit_recovery",
                "Flag submission and follow-up recovery handling.",
                ("flag", "submit", "retry", "recovery"),
                "Submit candidate flags immediately and use result feedback to decide next step.",
                ("track1", "track2", "track3", "track4"),
            ),
        ]

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
