---
name: tool-frp-stowaway
description: Use when you need a practical operating guide for frp and stowaway while building tunnels, pivots, and reverse reachability.
---

# Tool Guide: frp and Stowaway

## Overview

Use this skill when you need a stable route between the target and the callback server.

## When to Use

- The target must call back to your public IP.
- Lateral movement requires reusing a compromised host as a pivot.
- You need a SOCKS or reverse forwarding path for follow-on tools.

## Recommended Workflow

1. Prefer `frp` for straightforward reverse/forward tunnels and service exposure.
2. Prefer `stowaway` when multi-hop or segmented routing is required.
3. Keep one documented tunnel per immediate objective.
4. Tear down or rotate stale tunnels once the objective changes.

## Practical Notes

- For this environment, the default public callback host is `129.211.15.16`.
- `stowaway_admin -l` is a valid listener form in this environment; verify the port and route plan before deploying the agent side.
- Record listener address, exposed internal service, and cleanup path.
- Use `proxychains4` only after the SOCKS path is verified.
- For reverse shells and relay one-offs, `socat` may still be the lightest option.

## Resource Guardrails

- Do not keep overlapping tunnels alive without purpose.
- Avoid high-frequency reconnect loops that burn CPU or reveal presence.
