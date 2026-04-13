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

## Concrete CVE Leads

- `GHSA-rhm9-gp5p-5248`:
  Gradio `5.0.0` to `5.4.0` allowed arbitrary file read via crafted `FileData.path` values in `File` or `UploadButton` components. If `/config` reveals file-oriented inputs or upload widgets, test whether a request can pass attacker-chosen server-side paths back into the backend file helpers.
- `Queue/state abuse`:
  Even without a published CVE, many CTF-style Gradio services expose dangerous backend functions through `/config` and rely on client-side UI constraints. Treat hidden `api_name` / `fn_index` pairs as direct backend entrypoints and validate them manually.

## Exploit Playbook

1. Pull `/config` and identify every backend function plus any file-capable input/output component.
2. Test direct `/run/<api_name>` and `/run/predict` calls with your own `session_hash`, not only browser-derived requests.
3. If file components exist, try controlled `FileData.path` style mutations and compare server responses for allowlist failures versus successful reads.
4. If workflow functions mutate state, sequence calls in the same `session_hash` and inspect whether one backend function unlocks another.

## Helper Script

Use the bundled mapper first:

```bash
uv run python scripts/exploit_helpers/gradio_map.py --base-url http://TARGET:PORT
```

It will:
- fetch `/config`
- enumerate `fn_index`, `api_name`, `backend_fn`, inputs, outputs, and queue behavior
- produce a JSON function map that you can replay manually through `/run/<api_name>`

## Common Mistakes

- Guessing `fn_index` values without reading `/config`.
- Treating Gradio like a normal REST API and ignoring `session_hash` or component state.
- Burning time on local environment setup before exhausting the exposed Gradio HTTP surface.
