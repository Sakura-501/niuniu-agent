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

## Concrete CVE And Advisory Paths

- `CVE-2025-3466`:
  Versions `1.1.0` to `1.1.2` with the code execution node enabled. Treat this as an authenticated code-node escape/RCE path. If you can create or modify workflows/apps, inspect whether a code node can override globals or escape sandbox assumptions, then pivot to reading secrets, SSRF, or shell execution.
- `CVE-2024-11822`:
  Older `0.9.1` builds exposed an SSRF path. If the deployment looks old and still references remote file ingestion or backend fetch helpers, test URL-based import/fetch features against loopback and internal HTTP targets.
- `GHSA-6pw4-jqhv-3626`:
  Unauthorized access and modification of APP orchestration. If app/workflow IDs are guessable or exposed through the frontend, test direct object access and unauthorized orchestration edits before attempting deeper exploit chains.

## Exploit Playbook

1. Confirm Dify-specific frontend evidence: `data-api-prefix`, `data-public-api-prefix`, `/install`, `/init`, `/signin`, marketplace or app explorer routes.
2. Diff same-origin requests versus direct backend paths. If direct `/console/api` fails but the UI still works, the exploit path is probably a frontend bridge.
3. For old builds, prioritize SSRF and remote file fetch. For mid/newer builds, prioritize auth/control-plane paths and workflow or code-node abuse.
4. If you gain authenticated control, immediately test app/workflow modification, dataset connectors, remote file imports, and any code-capable execution node.

## Common Mistakes

- Repeatedly probing `127.0.0.1:5001` directly when only the frontend can reach it.
- Ignoring install/init state because the page itself looks like a simple Next.js site.
- Spending time on generic package CVEs before proving the observed Dify version and deployment path fit.
