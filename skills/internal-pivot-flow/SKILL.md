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

## Guardrails

- Avoid aggressive gateway probes that can hang or kill the target.
- Do not keep overlapping tunnels alive.
- Treat every new container as a fresh run; revalidate paths and footholds.
