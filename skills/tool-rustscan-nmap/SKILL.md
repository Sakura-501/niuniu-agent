---
name: tool-rustscan-nmap
description: Use when you need a practical operating guide for rustscan and nmap in IP-first internal assessments.
---

# Tool Guide: rustscan and nmap

## Overview

Use this skill when the target is an IP or segment and you need a reliable scan sequence instead of ad hoc port probing.

## When to Use

- The target is mainly an IP, not a public domain.
- You need fast port discovery followed by service validation.
- You want to keep scan noise and memory use under control.

## Recommended Workflow

1. Use `rustscan` for fast TCP discovery on a single host.
2. Pass discovered ports to `nmap -sV -sC` for service and version validation.
3. Use `nmap -p-` only when the host is worth a full sweep.
4. Use `masscan` only for larger ranges and always cap rate.

## Practical Notes

- `rustscan` is discovery-first, not replacement for validation.
- `nmap` output should be summarized into service, version, and next-action notes.
- For internal scanning, prefer one host at a time unless lateral scope demands more.

## Resource Guardrails

- Do not run full-range `nmap` against many hosts in parallel.
- Use bounded rate and concurrency.
- Kill stale scans once the answer is clear.
