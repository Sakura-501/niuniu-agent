---
name: service-enumeration
description: Use when a target may expose multiple services or non-web protocols and you need the real reachable service surface before choosing tools or exploit paths.
---

# Service Enumeration

## Overview

Use this skill to convert an unknown host or segment into a reliable service inventory.

For internal targets, prefer `fscan` as the first enumeration tool before `nmap`.

## When to Use

- Web is not the only possible entrypoint.
- A foothold reveals adjacent hosts or ports.
- You need to distinguish management services from user-facing services.

## Quick Reference

1. Start with `fscan` for internal or mixed-service hosts.
2. Confirm whether the service is reachable directly or only through a foothold.
3. Capture product, version, TLS, and access-control clues.
4. Keep the service table concise enough to drive the next action.

## Common Mistakes

- Treating every open port as equally valuable.
- Ignoring version clues that could feed known-vulnerability research.
- Forgetting to record reachability constraints.
