---
name: gradio-api-abuse
description: Use when a target exposes Gradio-specific routes such as /config, /run/predict, fn_index, api_name, session_hash, or /file= and you need a protocol-aware path from frontend state to backend function abuse.
---

# Gradio API Abuse

## Overview

Use this skill when the target is a Gradio app and the shortest path is through Gradio's own API semantics, not generic web fuzzing. The core task is to map backend functions and state transitions from `/config`.

## When to Use

- `/config` is reachable or JS assets clearly belong to Gradio.
- Responses mention `fn_index`, `api_name`, `session_hash`, queueing, or component state.
- The app exposes `/run/*`, `/api/*`, `/file=`, examples, or other Gradio helper routes.

## Quick Reference

1. Pull `/config` and map `dependencies`, `api_name`, `fn_index`, inputs, outputs, and queue settings.
2. Build minimal requests for `/run/<api_name>` or `/run/predict` with explicit `session_hash`.
3. Test state transitions, hidden functions, file access restrictions, and component update flows one function at a time.
4. Keep notes on which backend functions are stateful, which mutate data, and which return attacker-controlled output.

## Common Mistakes

- Guessing `fn_index` values without reading `/config`.
- Treating Gradio like a normal REST API and ignoring `session_hash` or component state.
- Burning time on local environment setup before exhausting the exposed Gradio HTTP surface.
