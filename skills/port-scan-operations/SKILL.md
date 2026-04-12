---
name: port-scan-operations
description: Use when you need fast and structured port and service discovery with rustscan, nmap, or masscan before choosing an exploit path.
---

# Port Scan Operations

## Overview

Use this skill to convert an IP or segment into a reliable service map without wasting time or memory.

## When to Use

- A host or segment may expose non-web services.
- A foothold reveals lateral targets.
- You need to decide between `rustscan`, `nmap`, and `masscan`.

## Tool Selection

- `rustscan`: fast TCP discovery on a single host, then hand off open ports to `nmap`.
- `nmap`: service detection, NSE, TLS clues, OS fingerprints, validation after a fast scan.
- `masscan`: large-range discovery only when rate control and collateral risk are understood.

## Quick Reference

1. Start with a bounded fast scan before deep fingerprinting.
2. Use `rustscan` or `masscan` for discovery, then confirm with `nmap`.
3. Record open port, protocol, service, banner, version, and reachability.
4. Avoid full-range aggressive scans unless the target and memory budget allow it.

## Resource Guardrails

- Prefer one host at a time unless a range scan is required.
- Cap concurrency and rate; do not run `masscan` or full-range `nmap` blindly.
- Save concise structured results instead of giant raw outputs.
