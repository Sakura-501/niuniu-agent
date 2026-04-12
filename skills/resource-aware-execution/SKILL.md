---
name: resource-aware-execution
description: Use when scans, exploit tooling, or long-running enumeration must be constrained to avoid exhausting CPU, memory, network, or challenge stability.
---

# Resource-Aware Execution

## Overview

Use this skill whenever tooling scale itself can become the problem.

## When to Use

- The host is small, shared, or already under heavy load.
- You are about to run recursive discovery, template scans, or multi-target sweeps.
- The challenge will stall or crash if tooling is too aggressive.

## Quick Reference

1. Choose the smallest scan that can answer the current question.
2. Set explicit scope, rate, thread, and timeout bounds.
3. Prefer sequential confirmation over parallel noise when memory is tight.
4. Kill or reschedule stale jobs when they stop producing signal.

## Guardrails

- Avoid stacking multiple heavy tools at once.
- Do not recurse deeply and scan full port ranges simultaneously.
- Treat large outputs as a memory risk; summarize early and discard noise.
