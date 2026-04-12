---
name: tunnel-and-pivot-operations
description: Use when a foothold must be converted into stable reachability with frp, stowaway, socat, proxychains, or similar pivot channels.
---

# Tunnel and Pivot Operations

## Overview

Use this skill to turn an unstable shell or segmented foothold into a deliberate reachability path for the next action.

## When to Use

- The target can reach back to the callback server but inbound access is blocked.
- Lateral movement requires exposing internal services locally.
- Tooling must be proxied through a foothold rather than executed on the target directly.

## Tool Selection

- `frp`: stable reverse/forward tunnels and service exposure.
- `stowaway`: multi-hop pivoting in segmented networks.
- `socat`: quick relays, reverse shells, and ad hoc port forwarding.
- `proxychains4`: force follow-on tools through an established SOCKS path.

## Quick Reference

1. Choose the minimum tunnel that enables the next deterministic step.
2. Prefer reversible, low-footprint forwarding over permanent infrastructure.
3. Tie every tunnel to a concrete next-hop or service objective.
4. Record listener port, exposed internal service, and cleanup steps.

## Resource Guardrails

- Do not keep multiple overlapping tunnels alive without need.
- Prefer a single stable route over many temporary channels.
- Kill stale relays and background agents when the objective changes.
