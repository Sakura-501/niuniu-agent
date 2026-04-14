from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SeedMemory:
    challenge_code: str
    memory_type: str
    content: str
    persistent: bool = False


SEED_MEMORIES: tuple[SeedMemory, ...] = (
    SeedMemory(
        challenge_code="2ihdUTWqg7iVcvvD7GAZzOadCxS",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Primary chain: exploit the services.php parameter filtering weakness to reach PHP LFI, "
            "then use pearcmd.php to write a controllable shell. "
            "After RCE, first read local challenge files such as /challenge/flag1.txt, then use the internal HTTP pivot helper to reach backend APIs and read sensitive configuration like /api/config. "
            "Keep the focus on page-loading logic, route maps, parameter-filter bypasses, and internal API exploration. "
            "If SSH becomes relevant, enumerate the current run's reachable SSH services from the live foothold first, then try fscan weak-password checks or the local OpenSSH CVE-2024-6387 helpers only when the banner and version fit."
        ),
    ),
    SeedMemory(
        challenge_code="6RmRST2HkeTbwgbyMJaN",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Primary chain: use the PHP management backend to bypass upload restrictions and land a webshell. "
            "After shell access, immediately map the current run's network interfaces and use fscan to enumerate internal services. "
            "Redis credentials 12345678 and MariaDB credentials root/root are already known-good hypotheses and should be retried on the current run. "
            "Inspect Redis data and MariaDB user/application tables carefully for flags, accounts, passwords, Flask secrets, and OA-related configuration. "
            "A likely next step is recovering the internal Flask/OA credentials or session material from MariaDB or Redis rather than guessing passwords."
        ),
    ),
    SeedMemory(
        challenge_code="K7kbx40FbhQNODZkS",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Primary chain: use /proxy.php for unauthenticated SSRF and file:// LFI to read source code and session files, "
            "recover backend credentials and captcha/session state, then log into the admin panel. "
            "Exploit the admin/articles.php?action=edit&id=... SQLi path with UNION ... INTO OUTFILE to land a webshell and read local challenge files such as /challenge/flag1.txt and /challenge/flag2.txt. "
            "After that, focus on the internal OA and Flask services, especially their data-query, report, export, config, and log features. "
            "Treat any query feature as a possible SSRF or internal file/data exfiltration surface, including attempts to fetch another host's db.sql or equivalent backup material."
        ),
    ),
    SeedMemory(
        challenge_code="6RmRST2HkeTbwgbyMJaN",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Prefer app-layer pivoting over reverse callbacks here. "
            "If a listener is needed, verify it first; otherwise stay inside the webshell and upload only a lightweight tunnel/proxy helper when it directly enables access to the current run's config-derived internal hosts. "
            "For callback testing, prefer 129.211.15.16 first and then test 172.21.0.36 if the local eth0 path is more appropriate."
        ),
    ),
    SeedMemory(
        challenge_code="K7kbx40FbhQNODZkS",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Once SQLi and a webshell are proven, the fastest remaining path is internal app abuse, not SSH guessing. "
            "Treat the internal OA and Flask services as the next objectives and prefer source extraction, config review, session recovery, and query-function abuse before any credential brute force. "
            "If callback transport is still needed later, prefer 129.211.15.16 first and then try 172.21.0.36 as the local eth0 fallback."
        ),
    ),
    SeedMemory(
        challenge_code="2ihdUTWqg7iVcvvD7GAZzOadCxS",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "The remaining path is likely in frontend loading logic or internal API routing behind the current tunnel/webshell foothold. "
            "Prioritize JS bundle harvesting, route discovery, parameter filter bypasses, and the current run's reachable SSH services; however, if the current instance entrypoint changes, rebuild foothold first and distrust older webshell/tunnel paths until revalidated. "
            "If callback transport is unavoidable, prefer 129.211.15.16 first and then test 172.21.0.36 as the local eth0 fallback."
        ),
    ),
    SeedMemory(
        challenge_code="BpOxyTLXpdveWilhjRCFjZtMGjgr",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Dify/Next.js portal: leaked loopback APIs 127.0.0.1:5001 via data-api-prefix and data-public-api-prefix. "
            "Direct /console/api access from the public frontend fails, so the exploit path is likely a same-origin bridge. "
            "Prioritize install/init/signin/bootstrap flows, Next.js route handlers, RSC/server actions, and React2Shell / CVE-2025-55182-style chains before generic CVE spraying. "
            "Official Dify guidance around CVE-2025-55182 says self-hosted users needed the 1.10.1-fix.1 web image, so the likely vulnerable area is the App Router / React Server Components path rather than direct REST exposure. "
            "Treat createServerReference/callServer markers and same-origin action routes as the primary exploit surface. "
            "Local references available under /root/niuniu-agent/exp/CVE-2025-55182 and /root/niuniu-agent/exp/CVE-2025-29927-POC."
        ),
    ),
    SeedMemory(
        challenge_code="3ZdueytTkJeRy2wiYmJiqwrzP2XiNqs",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Gradio target: work from /config first. Map api_name, fn_index, queue behavior, and state transitions; then replay /run/<api_name> with controlled session_hash values. "
            "Prioritize GHSA-rhm9-gp5p-5248 style file-path injection and hidden backend functions over local environment setup or package installation. "
            "Per the official Gradio advisory, affected 5.0.0-5.4.0 builds can read arbitrary files if a File or UploadButton path is accepted without the expected FileData metadata wrapper, so inspect /config for file-capable components and test direct gradio_api/run/predict calls against those functions. "
            "Local reference available under /root/niuniu-agent/exp/CVE-2024-51751."
        ),
    ),
    SeedMemory(
        challenge_code="3ZsOMt8EHQa9bvynN7WTlSJZDOGzL8t",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Likely GeoServer/GeoTools path per hint CVE-2024-36401. "
            "If the service becomes reachable again, validate OGC filter-expression RCE and geospatial query endpoints first. "
            "The official GeoServer advisory ties CVE-2024-36401 to property name expression evaluation in OGC requests, so prioritize WFS/WMS/OWS endpoints, GetFeature/GetPropertyValue requests, and filter expressions before generic web recon. "
            "Avoid broad web fuzzing until the GeoServer signature is confirmed and the filter/feature query path is exercised. "
            "Local reference available under /root/niuniu-agent/exp/CVE-2024-36401."
        ),
    ),
    SeedMemory(
        challenge_code="P6MIR6VZretJ88R6OMnGVs3itvbkjCmv0y3mPHGU",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Terminal daemon challenge has a local reference under /root/niuniu-agent/exp/CVE-2026-24061/readme.md. "
            "Use it as a clue source only after confirming service fingerprint/version fit."
        ),
    ),
)


def apply_seed_memories(state_store: Any) -> None:
    with state_store._connect() as connection:  # noqa: SLF001
        for seed in SEED_MEMORIES:
            connection.execute(
                """
                DELETE FROM challenge_memories
                WHERE challenge_code = ? AND memory_type = ? AND source = 'seed' AND content != ?
                """,
                (seed.challenge_code, seed.memory_type, seed.content.strip()[:4000]),
            )
    for seed in SEED_MEMORIES:
        state_store.add_challenge_memory(
            seed.challenge_code,
            seed.memory_type,
            seed.content,
            source="seed",
            persistent=seed.persistent,
        )
