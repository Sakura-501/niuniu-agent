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

## Common Mistakes

- Treating the UI like a normal CMS and missing the separate control plane.
- Probing only direct backend ports even when the real path is a same-origin proxy or server action.
- Installing local dependencies before exhausting the exposed HTTP API and shipped frontend code.
