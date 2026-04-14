---
name: tool-ligolo-sshuttle
description: Use when a track3 or track4 challenge needs a fast internal pivot and you want concrete operator guidance for ligolo-ng or sshuttle instead of generic tunnel advice.
---

# Ligolo / SSHuttle Operations

## Overview

Use this skill when you already have a foothold and need a practical pivot, especially for multi-hop internal service access.

## When to Use

- You need a userspace pivot to browse internal HTTP, Redis, DB, or SSH targets.
- `proxychains` alone is too awkward or noisy for the next step.
- You need a quick choice between Ligolo and SSHuttle.

## Quick Reference

- `ligolo-ng`:
  - better when you want a cleaner agent/proxy model
  - use for repeated internal service access and multi-host follow-on
- `sshuttle`:
  - useful when you already have SSH creds and need a quick route-based pivot

For this environment, prefer public callback host `129.211.15.16` first; if the local eth0 path is more appropriate, also test `172.21.0.36`.

## Common Mistakes

- Starting a heavy pivot before proving the next internal target exists.
- Forgetting cleanup and route rollback.
- Building a tunnel first and only then deciding what host to test.
