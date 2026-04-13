---
name: tool-winpeas-windows-assets
description: Use when you need a practical operating guide for staged Windows privilege-escalation assets such as winPEAS.
---

# Tool Guide: winPEAS and Windows Backup Assets

## Overview

Use this skill when a Windows foothold exists and you need portable Windows-side enumeration assets.

## When to Use

- The target is Windows and Linux-native tooling is no longer enough.
- You need a staged local privilege-escalation enumeration binary.
- You want to use archived Windows assets already cached on the operator host.

## Recommended Workflow

1. Confirm OS, architecture, and transfer path first.
2. Select the smallest asset that fits the target architecture.
3. Run the asset only when the local Windows foothold justifies it.
4. Save findings into notes and memory, not giant raw dumps.

## Practical Notes

- On the operator host, archived Windows assets are expected under the local tools cache.
- Prefer `winPEASx64.exe` for 64-bit Windows footholds and keep transfer steps explicit.

## Resource Guardrails

- Treat Windows assets as staged payloads, not local Linux commands.
- Do not transfer multiple redundant binaries if one already answers the current question.
