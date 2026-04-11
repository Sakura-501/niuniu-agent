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
    "known-vulnerability-mapping": SkillBehavior(
        trigger_keywords=("cve", "version", "apache", "nginx", "spring", "grafana", "fastapi"),
        usage_guidance="Normalize product and version clues, then rank likely known-vulnerability paths by fit.",
        recommended_tracks=("track2",),
    ),
    "web-vulnerability-testing": SkillBehavior(
        trigger_keywords=("sqli", "xss", "upload", "ssti", "idor", "auth", "template"),
        usage_guidance="Exploit only after reconnaissance confirms a likely path, and keep the winning request reproducible.",
        recommended_tracks=("track1", "track2"),
    ),
    "api-workflow-testing": SkillBehavior(
        trigger_keywords=("api", "json", "token", "jwt", "graphql", "rest"),
        usage_guidance="Prefer structured request/response diffing, auth flow checks, and minimal payload mutations.",
        recommended_tracks=("track1", "track2"),
    ),
    "cloud-asset-assessment": SkillBehavior(
        trigger_keywords=("cloud", "bucket", "metadata", "ai", "model", "inference", "llm"),
        usage_guidance="Check metadata, object storage, model-serving APIs, and exposed infrastructure control points.",
        recommended_tracks=("track2",),
    ),
    "lateral-movement-planning": SkillBehavior(
        trigger_keywords=("pivot", "lateral", "internal", "foothold", "next hop"),
        usage_guidance="Track the current foothold, next reachable asset, and the least wasteful pivot option.",
        recommended_tracks=("track3", "track4"),
    ),
    "privilege-path-analysis": SkillBehavior(
        trigger_keywords=("privesc", "sudo", "capability", "credential", "persistence"),
        usage_guidance="Enumerate privilege paths, reusable credentials, and long-lived access opportunities.",
        recommended_tracks=("track3", "track4"),
    ),
    "directory-identity-enumeration": SkillBehavior(
        trigger_keywords=("domain", "ad", "ldap", "kerberos", "dc", "smb"),
        usage_guidance="Map identity infrastructure, core hosts, trust edges, and the shortest path to privileged access.",
        recommended_tracks=("track4",),
    ),
    "evidence-capture": SkillBehavior(
        trigger_keywords=("flag", "submit", "retry", "recovery"),
        usage_guidance="Capture the minimal evidence set, submit valuable artifacts immediately, and use feedback to branch cleanly.",
        recommended_tracks=("track1", "track2", "track3", "track4"),
    ),
}


class SkillRegistry:
    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or self.default_skills_dir()
        self.skills = self._load_skills()

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

    def describe_available(self) -> str:
        if not self.skills:
            return "(no skills available)"
        return "\n".join(
            f"- {skill.name}: {skill.description}"
            for skill in sorted(self.skills, key=lambda item: item.name)
        )

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
