---
name: port-scan-operations
description: Use when you need fast and structured port and service discovery before choosing an exploit path, especially on internal targets where fscan should usually be the first scanner.
---

# Port Scan Operations

## Overview

Use this skill to convert an IP or segment into a reliable service map without wasting time or memory. On internal targets, default to `fscan` first.

## When to Use

- A host or segment may expose non-web services.
- A foothold reveals lateral targets.
- You need to decide between `rustscan`, `nmap`, and `masscan`.

## Tool Selection

- `fscan`: first choice for internal hosts, mixed service environments, and fast vuln+service triage.
- `rustscan`: fast TCP discovery on a single host when `fscan` is not suitable.
- `nmap`: service detection, NSE, TLS clues, OS fingerprints, validation after a fast scan.
- `masscan`: large-range discovery only when rate control and collateral risk are understood.

## Quick Reference

1. Start with `fscan` on internal or mixed-service targets.
2. Use `rustscan` or `masscan` only when `fscan` is not the right fit.
3. Confirm uncertain results with `nmap`.
4. Record open port, protocol, service, banner, version, and reachability.
5. Avoid full-range aggressive scans unless the target and memory budget allow it.

## Resource Guardrails

- Prefer one host at a time unless a range scan is required.
- Cap concurrency and rate; do not run `masscan` or full-range `nmap` blindly.
- Save concise structured results instead of giant raw outputs.
