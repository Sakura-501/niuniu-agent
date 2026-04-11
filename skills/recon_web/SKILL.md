---
name: recon_web
description: Web attack surface discovery for portals, routes, parameters, and static clues.
trigger_keywords: web, portal, site, login, admin, dashboard, http
recommended_tracks: track1, track2
usage_guidance: Start with route discovery, parameter discovery, and tech stack identification before exploitation.
---

# Recon Web

Use this skill when the target exposes HTTP entrypoints and the next move is to map the attack surface cheaply.

## Goals

- Identify live paths, forms, APIs, and static assets.
- Capture enough evidence to choose the next exploit path.
- Avoid noisy brute force before confirming the framework and request patterns.

## Checklist

1. Fetch the root page and linked static assets.
2. Check robots, docs, OpenAPI, and obvious admin paths.
3. Diff status codes and response shapes for hidden endpoints.
4. Record promising parameters, route patterns, and framework hints.
5. Store concise notes before switching to exploitation.
