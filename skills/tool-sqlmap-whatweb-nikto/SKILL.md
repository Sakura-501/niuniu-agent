---
name: tool-sqlmap-whatweb-nikto
description: Use when you need a practical operating guide for sqlmap, whatweb, and nikto in IP-first web validation.
---

# Tool Guide: sqlmap, WhatWeb, and Nikto

## Overview

Use this skill when a web service has already been identified and you need fast fingerprinting or injection triage.

## When to Use

- You have an HTTP target and need quick framework or product clues.
- A parameter or endpoint looks injection-prone.
- You want a low-cost first-pass check before manual exploitation.

## Recommended Workflow

1. Use `whatweb` for fast tech fingerprinting.
2. Use `nikto` for low-signal but quick misconfiguration and dangerous file hints.
3. Use `sqlmap` only on narrowed parameters, not on every endpoint.
4. Manually confirm any promising hit.

## Resource Guardrails

- Keep `sqlmap` scoped to one request pattern at a time.
- Do not let `nikto` or `sqlmap` flood weak internal hosts.
