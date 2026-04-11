from __future__ import annotations

from dataclasses import dataclass

from niuniu_agent.skills.registry import CapabilitySkill, SkillRegistry
from niuniu_agent.skills.tracks import TRACK_PROFILES, infer_track


@dataclass(frozen=True, slots=True)
class SkillPlan:
    stage: str
    skills: list[CapabilitySkill]


STAGE_PRIORITY = {
    "recon": ("web-surface-mapping", "service-enumeration", "known-vulnerability-mapping", "cloud-asset-assessment"),
    "exploit": ("web-vulnerability-testing", "api-workflow-testing", "evidence-capture"),
    "post_exploit": ("lateral-movement-planning", "privilege-path-analysis", "directory-identity-enumeration", "evidence-capture"),
    "recovery": ("evidence-capture", "web-surface-mapping", "service-enumeration", "web-vulnerability-testing", "api-workflow-testing"),
}

TRACK_STAGE_PRIORITY = {
    ("track2", "recon"): ("known-vulnerability-mapping", "cloud-asset-assessment", "service-enumeration", "web-surface-mapping"),
}


def plan_skills(
    registry: SkillRegistry,
    description: str,
    runtime_state: dict[str, object] | None = None,
    notes: dict[str, str] | None = None,
    track: str | None = None,
) -> SkillPlan:
    runtime_state = runtime_state or {}
    notes = notes or {}
    effective_track = track or infer_track(description)
    selected_by_text = registry.select_for_text(description)
    selected = registry.select(description, track=effective_track)

    if "foothold" in notes:
        stage = "post_exploit"
    elif int(runtime_state.get("failure_count", 0) or 0) > 0:
        stage = "recovery"
    elif any(skill.name in {"web-vulnerability-testing", "api-workflow-testing"} for skill in selected_by_text):
        stage = "exploit"
    else:
        stage = "recon"

    priority = TRACK_STAGE_PRIORITY.get((effective_track, stage), STAGE_PRIORITY[stage])
    track_profile = TRACK_PROFILES.get(effective_track)
    track_priority = {name: idx for idx, name in enumerate(track_profile.recommended_skills)} if track_profile else {}
    ordered = sorted(
        selected,
        key=lambda skill: (
            priority.index(skill.name) if skill.name in priority else 999,
            track_priority.get(skill.name, 999),
            skill.name,
        ),
    )
    return SkillPlan(stage=stage, skills=ordered)
