---
name: dify-self-hosted-assessment
description: Use when a target looks like a self-hosted Dify deployment with Next.js frontend assets, install or init routes, loopback console APIs, or server-side route bridges that may expose internal control-plane functionality.
---

# Dify Self-Hosted Assessment

## Overview

Use this skill when Dify is externally exposed through a public frontend but the real control plane lives behind internal API prefixes such as `127.0.0.1:5001`. The main job is to find how the frontend can still reach that backend.

## When to Use

- HTML or RSC payloads expose `data-api-prefix`, `data-public-api-prefix`, `/install`, `/init`, `/signin`, or `/explore/apps`.
- Shipped JS shows Next.js server actions, route handlers, or helper functions for setup/login/bootstrap.
- Direct access to `/console/api` or backend ports fails, but frontend flows clearly depend on them.

## Quick Reference

1. Capture leaked frontend metadata such as internal API prefixes, edition flags, and feature toggles.
2. Inspect JS chunks for setup, init, signin, install, dataset, upload, and app-market flows.
3. Look for same-origin bridges: route handlers, server actions, middleware decisions, upload helpers, remote file fetchers, and image/file proxies.
4. Treat install/init/signin/bootstrap as the shortest paths to backend influence before trying unrelated CVEs.

## Common Mistakes

- Repeatedly probing `127.0.0.1:5001` directly when only the frontend can reach it.
- Ignoring install/init state because the page itself looks like a simple Next.js site.
- Spending time on generic package CVEs before proving the observed Dify version and deployment path fit.
