---
name: tool-socat-proxychains
description: Use when you need a practical operating guide for socat and proxychains during internal tunnel and relay operations.
---

# Tool Guide: socat and proxychains

## Overview

Use this skill when a quick relay, reverse connection, or proxied follow-on tool path is enough and a heavier pivot stack is unnecessary.

## When to Use

- You need a one-off reverse shell or TCP forward.
- A SOCKS path already exists and tools must be forced through it.
- You want a lighter option than `frp` or `stowaway`.

## Recommended Workflow

1. Use `socat` for local relays, reverse listeners, and port forwarding.
2. Use `proxychains4` only after the SOCKS path is confirmed working.
3. Record listener, relay direction, and cleanup.

## Resource Guardrails

- Avoid chaining many ad hoc relays without a clear next step.
- Tear down stale forwards promptly.
