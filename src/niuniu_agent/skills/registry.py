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
            loaded.append(
                CapabilitySkill(
                    name=meta.get("name", path.parent.name),
                    description=meta.get("description", "No description provided."),
                    trigger_keywords=self._parse_list(meta.get("trigger_keywords", "")),
                    usage_guidance=meta.get("usage_guidance", "Load the full skill body before acting."),
                    recommended_tracks=self._parse_list(meta.get("recommended_tracks", "")),
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
    def _parse_list(raw: str) -> tuple[str, ...]:
        value = raw.strip().strip("[]")
        if not value:
            return ()
        return tuple(part.strip().strip("'\"") for part in value.split(",") if part.strip())

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
