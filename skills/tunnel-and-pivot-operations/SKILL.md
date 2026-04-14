---
name: tunnel-and-pivot-operations
description: Use when a foothold must be converted into stable reachability with frp, stowaway, socat, proxychains, or similar pivot channels.
---

# Tunnel and Pivot Operations

## Overview

Use this skill to turn an unstable shell or segmented foothold into a deliberate reachability path for the next action. When a webshell or direct command execution already works, prefer forward access and foothold-local probing before reverse tunnels.

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

1. First ask whether the current webshell or command execution primitive already lets you probe the next host or upload a lightweight helper directly.
2. Choose the minimum tunnel that enables the next deterministic step.
3. Prefer reversible, low-footprint forwarding over permanent reverse infrastructure.
4. Tie every tunnel to a concrete next-hop or service objective.
5. Record listener port, exposed internal service, and cleanup steps.

Default callback host for this environment: `129.211.15.16`.

## Resource Guardrails

- Do not keep multiple overlapping tunnels alive without need.
- Prefer a single stable route over many temporary channels.
- Kill stale relays and background agents when the objective changes.
- Do not choose reverse callbacks by default when forward connections or direct foothold-side testing already answer the question.
