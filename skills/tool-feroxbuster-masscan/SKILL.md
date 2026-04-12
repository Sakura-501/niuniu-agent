---
name: tool-feroxbuster-masscan
description: Use when you need a practical operating guide for feroxbuster and masscan in larger or recursive internal discovery jobs.
---

# Tool Guide: feroxbuster and masscan

## Overview

Use this skill when discovery scope grows beyond the lightweight defaults and you need recursive content or high-rate port coverage.

## When to Use

- Recursive web content discovery is justified.
- The target range is large enough that `masscan` is appropriate.
- Simpler scans stopped producing new signal.

## Recommended Workflow

1. Use `feroxbuster` for recursive content discovery only after a narrower pass identified promising roots.
2. Use `masscan` for range-level TCP discovery and validate with `nmap`.
3. Always turn high-rate findings into a smaller validated target list.

## Resource Guardrails

- Constrain recursion depth, threads, and rate.
- Never run `masscan` and multiple recursive web scans blindly in parallel on a weak box.
