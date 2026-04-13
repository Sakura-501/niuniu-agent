---
name: tool-nuclei-fscan
description: Use when you need a practical operating guide for nuclei and fscan for CVE and common-service validation.
---

# Tool Guide: nuclei and fscan

## Overview

Use this skill when reconnaissance already produced enough service or product clues to justify automated vulnerability validation.

## When to Use

- You have banners, versions, titles, or framework clues.
- You need quick triage of common vulnerabilities or exposed services.
- You want to decide whether to continue with manual exploitation.

## Recommended Workflow

1. Fingerprint first with `httpx`, `whatweb`, or manual requests.
2. Use `fscan` first for internal host/service sweeps and common misconfiguration checks.
3. Use `nuclei` with narrow tags/templates whenever possible after product fit is known.
4. Manually verify every promising hit.

## Practical Notes

- `fscan` is the default first scanner for internal IP-driven exploration where service mix is still unclear.
- `nuclei` should be scoped by tags, severity, or template set.
- Treat both as triage tools, not as proof by themselves.

## Resource Guardrails

- Avoid running broad template sets against everything at once.
- Keep internal scans bounded to current scope.
