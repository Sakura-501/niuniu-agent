---
name: privesc_maintain
description: Privilege escalation and persistence planning.
trigger_keywords: privesc, sudo, capability, credential, persistence
recommended_tracks: track3, track4
usage_guidance: Enumerate privilege paths and capture credentials or long-lived access paths.
---

# Privesc Maintain

Use this skill when you already have code execution or shell access and need higher privilege or more stable control.

## Goals

- Find the shortest privilege path.
- Preserve credentials and host context.
- Avoid destructive persistence unless required by the challenge.

## Checklist

1. Enumerate sudo, capabilities, writable paths, services, and scheduled tasks.
2. Search for credentials, tokens, SSH keys, and reusable secrets.
3. Confirm whether escalation helps unlock the next flag-bearing asset.
4. Record what changed so the next agent turn can resume cleanly.
