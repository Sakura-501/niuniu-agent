---
name: tool-petitpotam-dfscoerce
description: Use when you need a practical operating guide for PetitPotam or DFSCoerce forced-authentication chains against AD or Windows hosts.
---

# Tool Guide: PetitPotam and DFSCoerce

## Overview

Use this skill when you already have a relay or certificate-abuse hypothesis and need a concrete coercion step to make a host authenticate outward.

## When to Use

- AD / Windows target can reach your callback or relay listener.
- You already know what will consume the coerced authentication.
- You need to trigger machine/DC authentication with minimal noise.

## Tool Locations

- `petitpotam`: `/root/niuniu-agent/tools/bin/petitpotam`
- `dfscoerce`: `/root/niuniu-agent/tools/bin/dfscoerce`
- Default public callback host for this environment: `129.211.15.16`

## Recommended Workflow

1. Confirm the sink first: relay target, AD CS endpoint, or capture listener.
2. Prefer the narrowest coercion path that matches the target RPC surface.
3. Run one host at a time and observe whether authentication is actually triggered.
4. If coercion works, immediately pivot into the next step instead of repeatedly re-triggering.

## Practical Notes

- `petitpotam` is the MS-EFSRPC path and is often useful when EFSRPC/LSARPC exposure exists.
- `dfscoerce` is the MS-DFSNM path and is useful when DFS namespace management RPC is reachable.
- These tools are wrappers that call the vendored Python scripts with `uv` and the needed Python dependencies.

## Example Patterns

```bash
petitpotam -h
dfscoerce -h
```

Use the callback/relay listener IP explicitly, usually `129.211.15.16`, unless a challenge-specific note says otherwise.

## Resource Guardrails

- Do not spam coercion attempts without a confirmed sink.
- Stop after a small number of failed attempts and reassess RPC reachability, signing, and relay viability.
