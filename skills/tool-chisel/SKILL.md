---
name: tool-chisel
description: Use when you need a practical operating guide for chisel as a lightweight tunnel or SOCKS pivot tool.
---

# Tool Guide: chisel

## Overview

Use this skill when you need a simpler reverse tunnel or SOCKS path than a full pivot framework.

## When to Use

- A reverse HTTP/WebSocket-style tunnel fits the environment.
- You need SOCKS or TCP forwarding from a foothold back to the callback host.
- You want a low-friction tunnel before escalating to more complex routing.

## Recommended Workflow

1. Start the server on the callback host with the minimum required features.
2. Launch the client from the foothold with the narrowest forwarding scope.
3. Verify the path before pointing other tools through it.
4. Record bind port, remote mapping, and teardown steps.

## Resource Guardrails

- Do not expose more ports than necessary.
- Prefer one stable tunnel over many overlapping forwards.
