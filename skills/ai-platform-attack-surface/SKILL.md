---
name: ai-platform-attack-surface
description: Use when a target looks like a self-hosted AI or LLM platform and you need to map the frontend, backend, workflow, plugin, and model-serving trust boundaries before exploit attempts.
---

# AI Platform Attack Surface

## Overview

Use this skill when the target is an AI application platform rather than a plain web app. The goal is to separate the public UI from the hidden control plane, model-serving layer, file paths, and workflow execution paths.

## When to Use

- Pages reference model providers, workflows, prompts, datasets, plugins, tools, or app stores.
- Frontend assets leak internal API prefixes, loopback hosts, or control-plane routes.
- The target appears to be Dify, Gradio, Open WebUI, Langflow, Flowise, Ragflow, or a similar self-hosted AI portal.

## Quick Reference

1. Fingerprint the product and version from HTML, JS chunks, API shapes, and frontend metadata.
2. Split the surface into public UI, same-origin backend routes, loopback/internal APIs, file fetch paths, and workflow execution endpoints.
3. Map high-value flows: install/init, login, dataset ingestion, remote file fetch, plugin/tool execution, workflow run, and app publishing.
4. Prefer server-side bridges and trusted workflow actions over direct brute force against hidden backend ports.

## Concrete CVE Leads

- `Next.js CVE-2025-29927`: if the target is self-hosted Next.js and auth depends on Middleware, test protected same-origin routes with crafted `x-middleware-subrequest` values and compare redirect/auth behavior against the baseline request.
- `Next.js CVE-2025-48068`: if the target is clearly a dev server, treat source and route metadata exposure as a clue source rather than a direct production exploit path.
- `AI workflow platforms such as n8n / Flowise / Langflow`: prefer expression-evaluation, tool-execution, and workflow-node paths when the UI exposes pipelines, prompt graphs, or tool orchestration.

## Exploit Playbook

1. Identify whether the frontend is public-only and the control plane is loopback/internal.
2. Check whether same-origin routes, server actions, or image/file helpers can still reach that internal control plane.
3. If the app is workflow-driven, look for user-controlled expressions, file fetchers, remote URL imports, code nodes, and plugin/tool execution.
4. Only after the platform mechanics are mapped should you try version-matched CVE paths.

## Common Mistakes

- Treating the UI like a normal CMS and missing the separate control plane.
- Probing only direct backend ports even when the real path is a same-origin proxy or server action.
- Installing local dependencies before exhausting the exposed HTTP API and shipped frontend code.
