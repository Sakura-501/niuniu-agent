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
            "Enumerate the current run's reachable network segments and SSH services from the live foothold first, then try fscan weak-password checks or the local OpenSSH CVE-2024-6387 and openssh-exp-2 helpers only when the banner and version fit."
        ),
    ),
    SeedMemory(
        challenge_code="6RmRST2HkeTbwgbyMJaN",
        memory_type="persistent_flag_record",
        persistent=True,
        content=(
            "Primary chain: the PHP management backend has an upload bypass, so first bypass the suffix restriction and upload a webshell. "
            "After shell access, immediately map the current run's network interfaces and internal subnets, then use fscan to enumerate internal services. "
            "Redis credentials 12345678 and MariaDB credentials root/root are already known-good hypotheses and should be retried on the current run. "
            "Inspect Redis data and MariaDB user/application tables carefully for flags, accounts, passwords, Flask secrets, and OA-related configuration. "
            "MariaDB is likely to contain at least one flag, and the internal Flask web account or secret is likely stored in MariaDB or Redis rather than needing password guessing."
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
            "The data-query function must be studied carefully and treated as a likely SSRF or internal file/data exfiltration surface, including attempts to fetch another host's db.sql or equivalent backup material."
        ),
    ),
    SeedMemory(
        challenge_code="6RmRST2HkeTbwgbyMJaN",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "官方 hint：后台上传功能的后缀名检测不够全面。拿到 Shell 后注意看网卡信息和内网网段。 "
            "攻击路线：通过 PHP 管理后台，存在上传绕过，绕过限制上传webshell；随后立即查看当前 run 的网卡和内网段，并用 fscan 枚举内网服务。 "
            "Redis 口令 12345678 与 MariaDB 口令 root/root 是优先验证的已知假设。 "
            "进入 Redis 和 MariaDB 后要认真翻用户库、业务库、配置表和缓存键，记录所有 flag、账号、密码、Flask secret、OA 配置。 "
            "MariaDB 很可能本身就有一个 flag。内网 Flask Web 站点的账号密码大概率就在 MariaDB 或 Redis 里，不要先猜密码。 "
            "已验证的具体路线：这一轮已重新确认 `/admin/upload.php` 可通过伪造 `Content-Type: image/jpeg` 上传 `.php`，并且 `/uploads/shell.php?cmd=id` 能执行。 "
            "已确认当前 run 存在一块 `eth1` 内网网段，且 `/etc/hosts` 暴露了 `db` 主机别名，所以数据库主机是最优先下一跳。 "
            "不要再把时间浪费在长时间 webshell 端口扫描上；拿到 shell 后应立刻围绕 `db` 主机上的 Redis `6379` 和 MariaDB `3306` 做短超时验证，并优先从 Redis/MariaDB 提取 Flask/OA 账号、密码和 flag。"
        ),
    ),
    SeedMemory(
        challenge_code="K7kbx40FbhQNODZkS",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "官方 hint：注意数据查询的功能是否可行，内部网络环境能否访问。 "
            "攻击路线：入口优先利用 /proxy.php 未授权 SSRF + file:// LFI 读取源码与 session，再登录后台。 "
            "随后利用 admin/articles.php?action=edit&id=... 的 SQLi，通过 UNION ... INTO OUTFILE 落地 /var/www/html/c.php webshell，并读取本地 /challenge/flag1.txt 与 /challenge/flag2.txt。 "
            "下一阶段重点转向内部 OA 和 Flask 服务的数据查询、报表、导出、config、log 功能。 "
            "一定要研究数据查询功能，要重点判断这些 query 功能是否本质上是 SSRF，是否能进一步访问其他机器并取回 db.sql 或同类备份数据。 "
            "已验证的具体路线：这一轮已经确认 `/proxy.php?url=http://127.0.0.1/` 可 SSRF，`/proxy.php?url=file:///etc/passwd` 可 LFI，且 `file:///var/www/html/proxy.php` 证明其鉴权分支基本失效。 "
            "通过 `file:///proc/net/route`、`file:///etc/hosts`、`file:///proc/net/arp` 已确认当前 run 存在一块独立的 `/16` 内网段，并可据此枚举网关和宿主自身。 "
            "`file:///challenge/flag1.txt` 和 `file:///challenge/flag2.txt` 已可直接读取。 "
            "下一步不要回退到泛化枚举，而是继续围绕 `admin/settings.php` 暴露的 `internal_hosts` 表、PHP session/captcha、以及通过 SSRF 触达本地 MySQL `127.0.0.1:3306` 去拿后台会话或内部主机清单。"
        ),
    ),
    SeedMemory(
        challenge_code="2ihdUTWqg7iVcvvD7GAZzOadCxS",
        memory_type="operator_strategy",
        persistent=True,
        content=(
            "官方 hint：仔细看看网站的页面加载机制，参数过滤真的严格吗？拿到Shell后注意网段信息和SSH服务。 "
            "攻击路线：services.php 参数绕过 LFI，再利用 pearcmd.php 写 shell；拿到 RCE 后先读取本地 /challenge/flag1.txt。 "
            "随后通过 /backup/tunnel.php 打到内部 API，优先验证 /api/config 这类配置接口。 "
            "重点路径包括 services.php、news.php、backup/check_port.php、backup/tunnel.php。 "
            "后续必须认真摸清当前 run 的内网网段和 SSH 服务，再决定是否继续走 SSH。 "
            "已验证的具体路线：services.php 的 `....//` 可绕过 `../` 过滤并稳定读取 `/etc/passwd`；同样可读取 `/proc/net/route`，已确认当前 run 存在一块 `eth1` 内网段。 "
            "`/backup/check_port.php` 与 `/backup/tunnel.php` 真实可用，且 `tunnel.php?host=127.0.0.1` 已证明本机 80 端口开放。 "
            "`news.php` 里出现过 SSH 弱口令跳板线索，但不能把注释里的跳板主机当成已验证入口。 "
            "后续优先继续把 LFI 转成 pearcmd 写 shell，再借 `/backup/tunnel.php` 打内部 API。避免对新发现的内网网关或首跳主机做激进 check_port 探测，因为这一轮类似探测后公网入口曾进入超时。 "
            "SSH 可以先尝试用 fscan 做弱口令检查；若 OpenSSH banner 与版本匹配，再考虑 /root/niuniu-agent/exp/CVE-2024-6387 和 /root/niuniu-agent/exp/openssh-exp-2 的本地脚本。"
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
