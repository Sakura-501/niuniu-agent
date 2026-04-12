---
name: linux-privilege-escalation
description: Use when Linux execution exists and you need a repeatable privilege-escalation workflow with linpeas, pspy, sudo checks, capability review, and service abuse.
---

# Linux Privilege Escalation

## Overview

Use this skill to run a disciplined Linux privesc workflow rather than a pile of unprioritized checks.

## When to Use

- You already have shell or command execution on Linux.
- Root or a more privileged account is likely needed.
- Service accounts, cron, sudo, capabilities, or writable paths may exist.

## Tool Selection

- `linpeas`: broad Linux privilege-escalation checklist and clue gathering.
- `pspy`: process monitoring for cron/service execution opportunities.
- Built-ins: `sudo -l`, capability inspection, writable path/service review, kernel/package checks.

## Quick Reference

1. Confirm current user, groups, sudo rights, capabilities, and writable service paths.
2. Run low-noise local enumeration before exploit execution.
3. Convert broad enumeration into a ranked path list.
4. Keep the exact escalation path and evidence in notes.

## Resource Guardrails

- Prefer short, bounded local enumeration over giant recursive filesystem crawls.
- Use `pspy` selectively and stop once the relevant execution pattern is observed.
- Do not launch public exploit code before confirming the local path is viable.
