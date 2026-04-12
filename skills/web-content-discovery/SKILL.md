---
name: web-content-discovery
description: Use when you need deterministic route, file, and hidden content discovery with ffuf, gobuster, or feroxbuster.
---

# Web Content Discovery

## Overview

Use this skill to enumerate directories, files, vhosts, and hidden endpoints without flooding the host or drowning in noise.

## When to Use

- A web target exists but the real route surface is unclear.
- You need admin paths, hidden APIs, backups, or alternate virtual hosts.
- Existing discovery output is too shallow or too noisy.

## Tool Selection

- `ffuf`: fast wordlist-driven path, parameter, and vhost discovery with precise filters.
- `gobuster`: simple, deterministic dir/vhost enumeration and quick second opinion.
- `feroxbuster`: recursive content discovery when a larger site map is worth the extra load.

## Quick Reference

1. Start with a narrow wordlist and clear status/size filters.
2. Split dir/file/vhost tasks instead of mixing everything in one scan.
3. Confirm hits manually before escalating.
4. Store only high-signal findings: path, status, size, title, and why it matters.

## Resource Guardrails

- Limit recursion depth and thread count on fragile targets.
- Prefer short, targeted scans over endless recursion.
- Stop or narrow scans when repeated 403/404 patterns add no new information.
