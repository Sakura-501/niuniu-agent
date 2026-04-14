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
            "Track 3 chain: the historical winning path used LFI in services.php via lang=....// traversal bypass, "
            "then PEAR-based RCE and internal pivot helpers such as backup/check_port.php and backup/tunnel.php. "
            "However, this challenge instance can drift between runs, and older webshell or tunnel paths may 404 after remap. "
            "Treat older footholds as low-trust when the current external entrypoint changes. "
            "For fresh runs, first revalidate the current entrypoint, rebuild foothold if needed, map the reachable internal network, then prioritize page-loading logic, route maps, and parameter-filter bypasses over SSH."
        ),
    ),
    SeedMemory(
        challenge_code="6RmRST2HkeTbwgbyMJaN",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Track 3 multi-hop chain: upload bypass -> PHP webshell/RCE as www-data. "
            "A recent successful run exposed an internal OA service, Redis, MariaDB, and a sibling web application behind the foothold. "
            "Redis password 12345678 and MariaDB root/root were validated; Redis data exposed stale inventory keys and an already-submitted flag, while MariaDB corporate tables only held stale config and submitted data. "
            "Key blocker is now OA auth bypass or Flask secret-key recovery, or a DB/Redis-to-container pivot beyond current creds. "
            "Network-architecture discovery remains mandatory on every new run because internal ranges drift. "
            "After any future flag submission, continue deeper into OA/DB/container paths instead of stopping."
        ),
    ),
    SeedMemory(
        challenge_code="K7kbx40FbhQNODZkS",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Track 3/4 key chain: /proxy.php had an empty auth guard, yielding unauthenticated SSRF + file:// LFI. "
            "Confirmed reads of /challenge/flag1.txt and /challenge/flag2.txt, admin takeover via captcha/session abuse, SQLi in /admin/articles.php?action=edit&id=..., and a planted webshell. "
            "A prior successful run exposed an OA application and a Flask core service behind the foothold. "
            "Two flags have already been submitted on this chain; remaining work is to extract exact source/config/session material for the internal OA and Flask services and exploit query/report/export or auth-bypass paths. "
            "Do not default to reverse callback or SSH/password spraying unless a concrete config or service banner justifies it."
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
            "Once SQLi + webshell are proven, the fastest remaining path is internal app abuse, not SSH guessing. "
            "Treat the internal OA and Flask services as the next objectives and prefer source/config/session extraction plus query-function abuse before any credential brute force. "
            "If callback transport is still needed later, prefer 129.211.15.16 first and then try 172.21.0.36 as the local eth0 fallback."
        ),
    ),
    SeedMemory(
        challenge_code="2ihdUTWqg7iVcvvD7GAZzOadCxS",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "The remaining path is likely in frontend loading logic or internal API routing behind the current tunnel/webshell foothold. "
            "Prioritize JS bundle harvesting, route discovery, and parameter filter bypasses; however, if the current instance entrypoint changes, rebuild foothold first and distrust older webshell/tunnel paths until revalidated. "
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
    for seed in SEED_MEMORIES:
        state_store.add_challenge_memory(
            seed.challenge_code,
            seed.memory_type,
            seed.content,
            source="seed",
            persistent=seed.persistent,
        )
