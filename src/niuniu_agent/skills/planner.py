from __future__ import annotations

from dataclasses import dataclass

from niuniu_agent.skills.registry import CapabilitySkill, SkillRegistry
from niuniu_agent.skills.tracks import TRACK_PROFILES, infer_track


@dataclass(frozen=True, slots=True)
class SkillPlan:
    stage: str
    skills: list[CapabilitySkill]


STAGE_PRIORITY = {
    "recon": ("recon_web", "recon_service", "cve_mapping", "cloud_ai_surface"),
    "exploit": ("exploit_web", "exploit_api", "flag_submit_recovery"),
    "post_exploit": ("pivot_lateral", "privesc_maintain", "domain_enum", "flag_submit_recovery"),
    "recovery": ("flag_submit_recovery", "recon_web", "recon_service", "exploit_web", "exploit_api"),
}

TRACK_STAGE_PRIORITY = {
    ("track2", "recon"): ("cve_mapping", "cloud_ai_surface", "recon_service", "recon_web"),
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
    elif any(skill.name.startswith("exploit_") for skill in selected_by_text):
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
