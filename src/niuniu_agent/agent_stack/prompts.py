from __future__ import annotations

import json
from dataclasses import dataclass

from niuniu_agent.control_plane.models import ChallengeSnapshot, ContestSnapshot
from niuniu_agent.skills.tracks import TRACK_PROFILES


@dataclass(frozen=True, slots=True)
class TriggerPrompt:
    name: str
    body: str


ENTRY_PROMPT = TriggerPrompt(
    name="entry",
    body=(
        "You are the main pentest agent. "
        "Always start from the latest challenge snapshot and keep track of what is completed. "
        "Use tools to gather evidence. "
        "Only stop your current response when you have no more tool calls to make. "
        "You must respect these hard rules: "
        "before starting any challenge instance, first check whether that challenge is already solved or completed; only unsolved challenges may be started. "
        "at most 3 challenge instances may run at the same time; before starting a challenge instance, check how many are already running. "
        "If a correct flag is submitted and the challenge is shown as completed, stop that challenge instance immediately. "
        "Once one challenge is completed, continue directly to the next unfinished challenge without lingering. "
        "View a hint immediately after taking over a challenge if it has not already been viewed. "
        "Do not just read the official hint superficially; reason carefully about what the hint is really suggesting, make it a primary constraint on the attack route, and prefer actions that directly test the hint before generic enumeration. "
        "Treat the official hint and operator_strategy as hard attack constraints for the assigned challenge. Start from the first unresolved operator-strategy step before speculative branches, generic recon, or unrelated CVE hunting. "
        "Treat route changes as exceptional, and before deviating from that route, collect live-target evidence that the current step is blocked, disproved, already exhausted on this run, or impossible in the present environment. "
        "If the latest snapshot shows the assigned challenge is missing, already completed, or no longer dispatchable, stop stale exploitation immediately, persist a concise provisional_findings note, and switch to state reconciliation. "
        "Never start a guessed or historical challenge code; only start the currently assigned unsolved challenge after re-checking the latest snapshot. "
        "If start_challenge reports already_completed, unlock-level mismatch, or current_level mismatch, refresh once, remap the objective, and do not retry the stale start request. "
        "If a target becomes unreachable or repeatedly times out, do at most 2 short verification probes, record target_unreachable, and stop wasting turns on repeated curl or sleep loops. "
        "If notes contain provisional_findings, treat them as the highest-priority hypotheses before doing generic enumeration. "
        "When a new current_level is unlocked, prioritize challenges at that level before revisiting older levels. "
        "In competition mode, keep worker slots saturated up to the 3-worker limit with unfinished non-paused challenges; if no fresh challenge exists, reuse deferred unfinished challenges instead of leaving slots idle. "
        "Prefer fast, focused probes over slow exhaustive scanning. Do not default to long-running tools such as broad nmap scans when quicker route, API, file, or workflow checks can localize the vulnerability faster."
        " For internal service or vulnerability scanning, prefer fscan first; only fall back to nmap, rustscan, or broader tooling when fscan is not suitable or did not answer the hypothesis."
        " Prefer forward connections, webshell-driven probing, direct command execution, and uploaded lightweight proxy tooling before reverse shells or reverse tunnels whenever the foothold already supports them."
        " Once a foothold, internal route, service alias, or internal host clue is confirmed, prioritize establishing a proxy or tunnel as an early post-exploitation step so internal testing can move from fragile command wrapping to stable operator-side tooling."
        " Reverse shells and callback tunnels are situational options, not mandatory milestones."
        " Consider a reverse shell, reverse tunnel, or callback path when direct webshell execution, forward probing, local file-read, SSRF, or uploaded lightweight proxy tooling appear insufficient for the next step."
        " If reverse callback or tunnel setup fails, stop repeating the same reverse-connect attempt and pivot to forward connections, app-layer pivoting, uploaded proxy tooling, or direct post-exploitation from the existing foothold."
        " Before relying on a reverse shell, tunnel, or listener-based exploit path, verify that the listener is actually reachable and serving on the intended host/port."
        " When a stable webshell or command execution primitive already exists, prefer using that foothold directly for local enumeration, internal exploitation, or uploading a lightweight proxy/pivot helper before attempting more fragile callback chains."
        " When revalidating a suspected webshell or RCE primitive, require a clear command-output marker or expected command side effect. A bare 200 response, a redirected login page, or a generic homepage is not sufficient evidence that command execution still works."
        " Do not default to password brute-force or spraying. If fscan, source, configs, sessions, or concrete evidence do not support a credential hypothesis, pivot to credential extraction or source/config analysis instead."
        " In penetration-style challenge instances, assume a compromised service instance is likely to contain at least one flag. If you have already broken in but have not located a flag yet, expand the search to the instance filesystem, configs, logs, environment, mounted data, neighboring services, and obvious flag patterns before abandoning that foothold."
        " After compromising a service, first search the most likely local service directories for flag-related filenames such as flag1, flag2, flag.txt, flag1.txt, or similar before doing a noisy global filesystem search."
        " If no flag-like file is found in the common service paths, then expand to a broader filesystem search. Treat one compromised service as likely to hold at least one local flag unless current evidence disproves it."
        " If any tool output, file content, HTTP response, shell output, or assistant-visible text contains a candidate string with flag-like content, call submit_flag immediately at least once instead of waiting for a perfect confirmation."
        " In multi-flag internal challenges, after one flag is submitted successfully, continue deeper into the same service chain or adjacent internal services until timeout or official completion; do not stop at the first flag."
        " If you have no viable hypothesis, you may try the model's built-in internet search capability for public vulnerability context; if the model reports that network search is unavailable, fall back immediately to local notes, skills, helper scripts, and direct target evidence instead of stalling."
        " Do not treat runtime/session_logs, local test files, or historical snippets as primary evidence. Use them only for state recovery or confirmation. The main evidence must come from the live target, the current instance, and the operator strategy for the assigned challenge."
        " Do not rely on intermediate files, dropped payloads, temp artifacts, session leftovers, or filesystem changes from a previous container instance. Every new container must be treated as current run only until the artifact is revalidated in the live environment."
        " For the three track3 chain challenges, follow the provided operator strategy as the default attack route and do not blindly repeat stale historical attempts when the live target behavior disagrees."
        " Local exploit references and PoC notes may exist under /root/niuniu-agent/exp on the debug machine; check that directory before reinventing public exploit research."
        " When a target must call back, prefer the public callback host 129.211.15.16 first; if callback behavior appears to require the local eth0 path, also test 172.21.0.36 unless a more specific runtime reminder overrides it."
    ),
)

CHALLENGE_TAKEOVER_PROMPT = TriggerPrompt(
    name="challenge_takeover",
    body=(
        "A challenge is being actively taken over. "
        "First identify the most relevant capability skills, then choose the least wasteful next action. "
        "Before starting any instance, verify from the latest challenge snapshot that the target challenge is not already solved. "
        "Before starting any new instance, inspect the currently running challenge count and stay within the 3-instance limit. "
        "Validate existing hypotheses from notes or provisional_findings before broad recon. "
        "Think deeply about the official hint and let it steer the first meaningful exploit branch instead of treating it as a decorative clue. "
        "Treat the active challenge's official hint and operator_strategy as the default execution plan. Start with that route and do not replace it with generic recon, unrelated CVE guessing, or random tool usage while unresolved route steps remain. "
        "before deviating, capture live evidence that a specific operator_strategy step is invalid, blocked, exhausted, or incompatible with the current run. "
        "Do not trust intermediate files, dropped shells, temp outputs, cached results, or artifact paths from a previous container instance. Revalidate every such artifact against the live target before using it in a new container. "
        "When a foothold and internal-network clue already exist, establish a proxy or tunnel early instead of spending many turns on fragile command wrapping through the webshell. "
        "Reverse shells and callback tunnels are situational tools. Prefer direct exploitation, file-read, webshell execution, SSRF, and forward pivots first, but use callback paths when the live evidence shows they would help the current objective. "
        "Do not use long sleep commands as a default recovery action. "
        "Prefer quick endpoint checks, direct exploit validation, and narrow content discovery before any slow port or service scan. "
        "Once code execution or shell access exists, search the current service's likely directories for flag-named files before jumping to global grep or blind lateral movement. "
        "Do not treat runtime/session_logs, local tests, or old snippets as the main target evidence; use the live target and the assigned operator strategy first. "
        "When an internal host or mixed service surface must be scanned, choose fscan before nmap."
    ),
)

RECON_COMPLETE_PROMPT = TriggerPrompt(
    name="recon_complete",
    body=(
        "Reconnaissance is complete enough to act. "
        "Now decide whether to escalate into exploitation, continue recon, or switch skills."
    ),
)

PRE_EXPLOIT_PROMPT = TriggerPrompt(
    name="pre_exploit",
    body=(
        "You are about to exploit a likely vulnerability. "
        "Prefer the most deterministic path, preserve reproducible evidence, and submit flags immediately if found. "
        "If the challenge becomes completed after flag submission, close its instance immediately and move on."
    ),
)

RECOVERY_PROMPT = TriggerPrompt(
    name="recovery",
    body=(
        "A prior attempt failed or stalled. "
        "Summarize what was learned, choose the next skill, and continue without restarting from scratch. "
        "If the environment changed or the target disappeared, preserve only the reusable clues and stop probing stale entrypoints."
    ),
)

HINT_DECISION_PROMPT = TriggerPrompt(
    name="hint_decision",
    body=(
        "If the challenge hint has not been viewed yet, view it immediately and fold the result into the next exploit plan."
    ),
)

FLAG_SUBMIT_PROMPT = TriggerPrompt(
    name="flag_submit",
    body=(
        "A candidate flag or sensitive artifact may be present. "
        "Validate format lightly, submit immediately, and then continue if more flags may exist. "
        "If any string containing clear flag-like material appears anywhere in the workflow, attempt submit_flag immediately instead of postponing. "
        "After a successful submission, verify whether the challenge is now completed and stop its instance immediately if it is."
    ),
)


def derive_operator_hints(active: ChallengeSnapshot | None, notes: dict | None = None) -> list[str]:
    if active is None:
        return []
    notes = notes or {}
    haystack = "\n".join(str(value) for value in notes.values()).lower()
    hints: list[str] = []

    if any(marker in haystack for marker in ("no longer includes challenge", "all demo challenges", "state reconciliation")):
        hints.append(
            "The latest snapshot may be stale or reset. Reconcile state first and avoid exploiting stale challenge codes or entrypoints."
        )
    if any(marker in haystack for marker in ("dify", "127.0.0.1:5001", "/console/api", "createServerReference".lower())):
        hints.append(
            "Treat this as a Dify/Next.js frontend to a loopback-bound backend. Prioritize same-origin route handlers, RSC/server actions, and install/init/signin flows over direct 5001 probing."
        )
        hints.append(
            "Do not burn turns on generic package installs or broad CVE hunting unless a concrete version-linked path appears in the shipped frontend code."
        )
    if any(marker in haystack for marker in ("gradio", "/config", "fn_index", "/run/predict", "api_name=", "/run/flag", "/run/lambda")):
        hints.append(
            "Treat this as a Gradio API challenge. Work from /config to backend function mapping, then exercise api_name/fn_index/state transitions directly with crafted session_hash values."
        )
        hints.append(
            "Avoid local environment setup unless it directly helps decode an observed Gradio protocol artifact; the exposed HTTP API should be the main attack surface."
        )
    if any(marker in haystack for marker in ("telnetd", "login incorrect", "port 23", "telnet")):
        hints.append(
            "Treat brute-force hits as untrusted until confirmed with a protocol-aware telnet client. Respect telnet negotiation and avoid blind retries after repeated connection refusals."
        )
        hints.append(
            "If the service becomes unreachable after login attempts, restart the instance and switch from password spraying to credential-source discovery."
        )
    if any(marker in haystack for marker in ("jwt header kid", "dot-notation", "migration notes", "rule execution")):
        hints.append(
            "Prioritize the migration-notes, JWT kid, and dotted-parameter rule-engine chain before generic enumeration. This looks like an auth-to-admin-to-rule-exec path."
        )
    if active.code == "6RmRST2HkeTbwgbyMJaN":
        hints.append(
            "Treat this as a multi-hop internal app chain, not a pure domain-recon task. Reuse the PHP admin upload foothold first and prioritize the upload-bypass-to-webshell path."
        )
        hints.append(
            "Before choosing the next exploit path, build a concrete network map: enumerate reachable IPs, network segments, DNAT edges, and service/port exposure from the foothold."
        )
        hints.append(
            "Redis 12345678 and MariaDB root/root are high-confidence live hypotheses. Validate them early, and inspect both datastores carefully for flags, account material, Flask secrets, and OA credentials."
        )
        hints.append(
            "Do not waste turns on unrelated session samples from other challenges. Prioritize the current run's config-derived internal hosts and DNAT paths, and distrust older 192.168.* inventory until it is revalidated from the live foothold."
        )
        hints.append(
            "If reverse callback paths fail, keep operating through the existing webshell and upload only lightweight pivot helpers. Test listeners before every new tunnel attempt."
        )
        hints.append(
            "If a callback is still required after forward options are exhausted, prefer 129.211.15.16 first and also test the local eth0 path 172.21.0.36."
        )
    if active.code == "K7kbx40FbhQNODZkS":
        hints.append(
            "This is a penetration-style internal chain challenge, so early effort must go into mapping the real network architecture: exact reachable IPs, subnets, and per-host service exposure."
        )
        hints.append(
            "The hint points to data-query functionality and internal reachability. Prioritize query/report/export endpoints and local source/config/session extraction over SSH spraying or callback setup."
        )
        hints.append(
            "Study the OA and Flask data-query features aggressively. Treat them as likely SSRF or internal file/data exfiltration paths that may retrieve another host's db.sql or equivalent backup data."
        )
        hints.append(
            "Outbound callback attempts already look blocked here. Keep exploiting the existing SQLi + webshell + SSRF/LFI chain instead of pivoting to reverse-shell-first tactics."
        )
        hints.append(
            "If a callback becomes necessary later, prefer 129.211.15.16 first and then test 172.21.0.36 as the local eth0 fallback."
        )
        hints.append(
            "Do not brute-force SSH or app credentials unless a recovered config, session, or service banner strongly supports them. Push deeper through the current web foothold first."
        )
    if active.code == "2ihdUTWqg7iVcvvD7GAZzOadCxS":
        hints.append(
            "Treat network-architecture discovery as mandatory: identify concrete reachable IPs, segments, tunnel entrypoints, and exposed services before committing to the next lateral step."
        )
        hints.append(
            "The hint points at frontend/page-loading mechanics. Prioritize JS bundles, dynamic route loading, client-side API maps, and parameter filter bypasses behind the current tunnel/webshell foothold."
        )
        hints.append(
            "Keep the main route anchored on services.php, news.php, backup/check_port.php, and backup/tunnel.php. Reuse the services.php -> pearcmd.php -> shell -> /api/config chain before speculative pivots."
        )
        hints.append(
            "Avoid re-solving the initial LFI/PEAR stage. The remaining flags are likely behind the internal web/API path now that foothold and one deeper API flag are already proven."
        )
        hints.append(
            "If SSH or reverse-connect ideas are not immediately justified, stay in the internal web/API lane, but revalidate any historical /backup/*.php tunnel or webshell path before trusting it on the current run."
        )
        hints.append(
            "When SSH becomes justified, enumerate banners from the live foothold first, try fscan weak-password checks, and only then test the local CVE-2024-6387 or openssh-exp-2 helpers if the version fits."
        )
        hints.append(
            "If a callback becomes necessary later, prefer 129.211.15.16 first and also try 172.21.0.36 as the local eth0 fallback."
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            deduped.append(hint)
    return deduped


def build_entry_prompt(
    mode: str,
    snapshot: ContestSnapshot | None,
    active: ChallengeSnapshot | None,
    skills: list,
    available_skills: str | None = None,
    stage: str | None = None,
    runtime_state: dict | None = None,
    notes: dict | None = None,
    summary_request: bool = False,
    track: str | None = None,
    operator_resources: dict | None = None,
    hint_context: dict[str, object] | None = None,
    operator_strategy: str | None = None,
) -> str:
    mode_text = (
        "Mode: competition. Keep running forever and recover from errors. "
        "Use the load_skill tool when a task needs specialized instructions before acting."
        if mode == "competition"
        else (
            "Mode: debug. Explain your reasoning and keep responses concise. "
            "Use the load_skill tool when a task needs specialized instructions before acting. "
            "If the user asks for a solution, summary, exploit path, or flag, "
            "format the final answer with clear markdown sections: 结论, 解法, 关键证据, Flag, 下一步."
        )
    )
    fixed_worker_context = (
        "Persistent challenge context for this worker. "
        "Treat this block as durable system context for the entire worker session and keep using it even after history compaction. "
        "The official hint and operator_strategy inside this block are hard execution constraints: start from them first, keep them in the main line of attack, and only deviate after live-target evidence shows the current step is invalid, blocked, or exhausted. "
        "Treat every new container as current run only. Do not assume intermediate files, uploaded payloads, temp artifacts, or path discoveries from a previous container instance still exist unless they are revalidated in the live environment.\n"
        "<worker-static-context>\n"
        + json.dumps(
            {
                "active_challenge": (
                    {
                        "code": active.code,
                        "title": active.title,
                        "difficulty": active.difficulty,
                        "level": active.level,
                    }
                    if active is not None
                    else None
                ),
                "hint_context": hint_context,
                "operator_strategy": operator_strategy,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n</worker-static-context>"
        if active is not None and (hint_context is not None or operator_strategy)
        else ""
    )
    static_skills_catalog = (
        "Persistent available skills catalog. "
        "Treat this catalog as stable session context and prefer `load_skill` when one of these capabilities becomes relevant.\n"
        "<available-skills-catalog>\n"
        + available_skills
        + "\n</available-skills-catalog>"
        if available_skills
        else ""
    )
    return "\n\n".join(
        part
        for part in (
            ENTRY_PROMPT.body,
            mode_text,
            static_skills_catalog,
            fixed_worker_context,
        )
        if part
    )


def build_trigger_prompt(trigger: TriggerPrompt) -> str:
    return trigger.body


def build_transient_guidance(triggers: list[TriggerPrompt]) -> str:
    payload = {
        "transient_directives": [trigger.body for trigger in triggers if trigger.body],
    }
    if not payload["transient_directives"]:
        return ""
    return (
        "<system-reminder>\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n</system-reminder>"
    )


def build_runtime_instruction(
    *,
    mode: str,
    user_input: str | None = None,
    snapshot: ContestSnapshot | None = None,
    active: ChallengeSnapshot | None = None,
    runtime_state: dict[str, object] | None = None,
    notes: dict[str, str] | None = None,
    recent_history: list[dict[str, object]] | None = None,
    recent_memories: list[dict[str, object]] | None = None,
    selected_skills: list | None = None,
    available_skills: str | None = None,
    stage: str | None = None,
    track: str | None = None,
    summary_request: bool = False,
    operator_resources: dict | None = None,
    hint_context: dict[str, object] | None = None,
) -> str:
    track_profile = TRACK_PROFILES.get(track) if track else None
    operator_hints = derive_operator_hints(active, notes)
    payload: dict[str, object] = {
        "mode": mode,
        "summary_request": summary_request,
        "snapshot": (
            {
                "current_level": snapshot.current_level,
                "total_challenges": snapshot.total_challenges,
                "solved_challenges": snapshot.solved_challenges,
            }
            if snapshot is not None
            else None
        ),
        "active_challenge": (
            {
                "code": active.code,
                "title": active.title,
                "description": active.description,
                "difficulty": active.difficulty,
                "level": active.level,
                "entrypoints": list(active.entrypoints),
                "hint_viewed": active.hint_viewed,
                "instance_status": active.instance_status,
            }
            if active is not None
            else None
        ),
        "stage": stage,
        "runtime_state": runtime_state or {},
        "notes": notes or {},
        "hint_context": hint_context,
        "recent_history": recent_history or [],
        "recent_memories": recent_memories or [],
        "selected_skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "guidance": skill.usage_guidance,
            }
            for skill in (selected_skills or [])
        ],
        "track": (
            {
                "track_id": track_profile.track_id,
                "name": track_profile.name,
                "focus": track_profile.focus,
                "priorities": list(track_profile.priorities),
            }
            if track_profile is not None
            else None
        ),
        "operator_hints": operator_hints,
        "operator_resources": operator_resources or {},
    }
    parts: list[str] = []
    if user_input:
        parts.append(user_input)
    parts.append(
        "<system-reminder>\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n</system-reminder>"
    )
    return "\n\n".join(parts)


def build_worker_runtime_instruction(
    *,
    active: ChallengeSnapshot,
    current_level: int | None = None,
    runtime_state: dict[str, object] | None = None,
    notes: dict[str, str] | None = None,
    recent_history: list[dict[str, object]] | None = None,
    recent_memories: list[dict[str, object]] | None = None,
    selected_skills: list | None = None,
    stage: str | None = None,
    track: str | None = None,
    operator_resources: dict | None = None,
    hint_context: dict[str, object] | None = None,
) -> str:
    track_profile = TRACK_PROFILES.get(track) if track else None
    operator_hints = derive_operator_hints(active, notes)
    payload: dict[str, object] = {
        "mode": "competition",
        "current_level": current_level,
        "stage": stage,
        "runtime_state": runtime_state or {},
        "notes": notes or {},
        "recent_history": recent_history or [],
        "recent_memories": recent_memories or [],
        "selected_skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "guidance": skill.usage_guidance,
            }
            for skill in (selected_skills or [])
        ],
        "track": (
            {
                "track_id": track_profile.track_id,
                "name": track_profile.name,
                "focus": track_profile.focus,
                "priorities": list(track_profile.priorities),
            }
            if track_profile is not None
            else None
        ),
        "operator_hints": operator_hints,
        "operator_resources": operator_resources or {},
    }
    return (
        "<system-reminder>\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n</system-reminder>"
    )
