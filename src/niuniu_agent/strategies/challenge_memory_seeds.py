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
            "Track 3/4 key chain: LFI in /services.php via lang=....// traversal bypass. "
            "Read /var/www/html/services.php, then include /usr/local/lib/php/pearcmd.php to write a PHP webshell under /tmp. "
            "Confirmed RCE as www-data and retrieved /challenge/flag1.txt. "
            "Next steps: enumerate internal pivot helpers backup/check_port.php and backup/tunnel.php, search foothold for SSH/private keys, and pivot toward 10.0.163.217/10.0.163.218 instead of re-solving the initial LFI stage."
        ),
    ),
    SeedMemory(
        challenge_code="6RmRST2HkeTbwgbyMJaN",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Track 4 key chain: upload bypass -> PHP webshell/RCE as www-data. "
            "Recovered PHP admin sessions from /tmp/sess_* with admin role and CSRF tokens. "
            "Internal OA reachable at 172.19.0.2:8080 and captcha value is exposed inside the signed Flask session cookie payload. "
            "Redis 172.19.0.3:6379 and MariaDB 172.19.0.3:3306 are reachable from the foothold. "
            "After any future flag submission, continue with OA session reuse, cookie decoding, Redis/MariaDB credential extraction, and deeper internal pivoting."
        ),
    ),
    SeedMemory(
        challenge_code="K7kbx40FbhQNODZkS",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Track 3/4 key chain: /proxy.php had an empty auth guard, yielding unauthenticated SSRF + file:// LFI. "
            "Confirmed reads of /challenge/flag1.txt and /challenge/flag2.txt and recovered /var/www/html/proxy.php. "
            "Additional source shows admin_articles.php SQLi on action=edit&id and admin_settings.php internal host inventory. "
            "Next steps: use proxy.php for internal HTTP reachability, exploit admin_articles SQLi, and inspect loopback MySQL/php-fpm plus 172.20.0.3:8080 / 172.20.0.5:80 internal apps for more flags."
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
            "Treat createServerReference/callServer markers and same-origin action routes as the primary exploit surface."
        ),
    ),
    SeedMemory(
        challenge_code="3ZdueytTkJeRy2wiYmJiqwrzP2XiNqs",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "Gradio target: work from /config first. Map api_name, fn_index, queue behavior, and state transitions; then replay /run/<api_name> with controlled session_hash values. "
            "Prioritize GHSA-rhm9-gp5p-5248 style file-path injection and hidden backend functions over local environment setup or package installation. "
            "Per the official Gradio advisory, affected 5.0.0-5.4.0 builds can read arbitrary files if a File or UploadButton path is accepted without the expected FileData metadata wrapper, so inspect /config for file-capable components and test direct gradio_api/run/predict calls against those functions."
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
            "Avoid broad web fuzzing until the GeoServer signature is confirmed and the filter/feature query path is exercised."
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
