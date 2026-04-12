---
name: tool-cloudfox
description: Use when you need a practical operating guide for cloudfox during cloud identity, asset, and permissions enumeration.
---

# Tool Guide: cloudfox

## Overview

Use this skill when you have cloud credentials or cloud-facing footholds and need fast situational awareness.

## When to Use

- You obtained cloud credentials, tokens, or metadata access.
- You suspect cloud storage, IAM, or account structure is in scope.
- You need to understand permissions before touching higher-risk actions.

## Recommended Workflow

1. Identify provider, account/project boundary, and credential type.
2. Use `cloudfox` to enumerate identity, high-value assets, and privilege clues.
3. Correlate outputs with the current challenge objective.
4. Convert broad cloud visibility into one concrete next action.

## Practical Notes

- `cloudfox` is strongest as a situational awareness tool, not a final exploitation step.
- Preserve the exact credential context used for each run.
- If the environment is AI/cloud-infra heavy, tie findings back to exposed model or storage surfaces.

## Resource Guardrails

- Stay read-only until the abuse path is justified.
- Keep runs scoped to the current authorized account/project.
