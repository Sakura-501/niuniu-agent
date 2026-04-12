---
name: tool-linpeas-pspy
description: Use when you need a practical operating guide for linpeas and pspy during Linux privilege escalation.
---

# Tool Guide: linpeas and pspy

## Overview

Use this skill when you already have Linux execution and need a repeatable local privilege-escalation flow.

## When to Use

- You have shell or command execution on Linux.
- You suspect sudo, cron, services, or writable paths may yield privilege escalation.
- You need process visibility without root.

## Recommended Workflow

1. Run bounded local checks first: user, groups, `sudo -l`, writable services, capabilities.
2. Use `linpeas` to widen coverage and collect high-signal escalation clues.
3. Use `pspy` to watch scheduled or service-driven execution when static checks are insufficient.
4. Convert findings into one ranked path instead of trying everything.

## Practical Notes

- `linpeas` is clue generation, not proof by itself.
- `pspy` is most useful when you already suspect cron or periodic execution.
- Keep command output summarized into actionable notes quickly.

## Resource Guardrails

- Stop `pspy` when you have enough evidence.
- Avoid giant recursive filesystem commands if `linpeas` already covered the same ground.
