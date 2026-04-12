---
name: tool-metasploit
description: Use when you need a practical operating guide for Metasploit Framework in internal exploitation, payload delivery, or session management.
---

# Tool Guide: Metasploit

## Overview

Use this skill when a framework-backed exploit, handler, or pivot workflow is worth the overhead.

## When to Use

- A known exploit or payload path already exists.
- You need a handler, staged payload, or framework-supported post-exploitation module.
- A manual exploit path is slower or less reliable than a tested Metasploit module.

## Recommended Workflow

1. Confirm the target and exploit fit before launching Metasploit.
2. Use `msfconsole` only after narrowing to a module family or payload need.
3. Record module name, target settings, LHOST/LPORT, and cleanup steps.
4. Prefer the lightest payload that solves the current problem.

## Practical Notes

- Metasploit is useful, but high overhead compared with single-purpose binaries.
- Reuse the callback server configuration already exposed to the agent.
- Prefer deterministic modules and avoid spraying modules across the whole host set.

## Resource Guardrails

- Do not leave idle handlers or stale sessions running without purpose.
- Avoid spinning up Metasploit if a simpler tool already solves the step.
