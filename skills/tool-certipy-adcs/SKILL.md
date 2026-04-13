---
name: tool-certipy-adcs
description: Use when you need a practical operating guide for certipy-ad and AD CS attack-path enumeration.
---

# Tool Guide: certipy-ad

## Overview

Use this skill when AD CS or certificate-based privilege paths are in scope.

## When to Use

- The environment includes AD CS, enterprise CAs, enrollment services, or template clues.
- You suspect ESC-style certificate abuse paths.
- A domain foothold already exists and certificate abuse may shorten the path.

## Recommended Workflow

1. Confirm domain reachability, credentials, and CA presence.
2. Use `certipy-ad` (or `certipy` if the packaged binary uses the shorter name) for discovery before trying certificate requests.
3. Rank findings by shortest path to privilege escalation or impersonation.
4. Save templates, CA names, and request parameters carefully.

## Resource Guardrails

- Do not enumerate every certificate path blindly if AD CS is not actually present.
- Keep credential and cert material tied to the exact host/domain used.
