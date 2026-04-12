---
name: tool-ffuf-gobuster
description: Use when you need a practical operating guide for ffuf and gobuster during internal web and service content discovery.
---

# Tool Guide: ffuf and gobuster

## Overview

Use this skill for deterministic path, file, and vhost discovery against IP-based or host-header driven applications.

## When to Use

- You already know an HTTP service exists.
- The application surface is larger than the default landing page.
- You need hidden routes, backups, APIs, or alternate virtual hosts.

## Recommended Workflow

1. Start with `ffuf` and a narrow wordlist plus response filters.
2. Use `gobuster` as a second opinion for directories or vhosts.
3. Confirm hits manually before escalating into exploitation.
4. Save only high-signal hits: path, status, size, title, and why it matters.

## Practical Notes

- Prefer separate passes for dirs, files, and vhosts.
- For IP-only targets, force `Host` header or vhost mode only if the app behavior suggests it.
- If 403s dominate, pivot into auth or misconfig analysis instead of endless brute discovery.

## Resource Guardrails

- Cap recursion and threads.
- Avoid giant wordlists until small ones stop producing signal.
