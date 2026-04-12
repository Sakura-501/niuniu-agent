---
name: tool-mimikatz-windows
description: Use when you need a practical operating guide for staging or using mimikatz as a Windows-side credential extraction asset.
---

# Tool Guide: Mimikatz (Windows Asset)

## Overview

Use this skill when Windows credential extraction is relevant and a Mimikatz payload may need to be staged on a Windows target.

## When to Use

- A Windows foothold exists and credential material is a realistic next step.
- You already know a Windows context exists; do not try to run it on Linux.
- The challenge objective justifies local Windows credential extraction or ticket work.

## Recommended Workflow

1. Treat `mimikatz` as a staged Windows artifact, not a local Linux tool.
2. Confirm OS, privilege level, and objective before transfer.
3. Prefer minimal commands and precise collection rather than running broad modules blindly.
4. Save the exact artifact path and what credentials/tickets were extracted.

## Practical Notes

- Use only when a Windows host is actually under your control.
- Pair with `impacket`, `netexec`, and `BloodHound` findings to decide whether extraction is necessary.
- Keep in mind that many challenge paths can be solved without full credential dumping.

## Resource Guardrails

- Avoid staging large Windows-only assets unless the foothold is stable enough to use them.
- Do not treat archived Windows artifacts as proof that the Linux side can execute them.
