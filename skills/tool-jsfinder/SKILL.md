---
name: tool-jsfinder
description: Use when you need a practical operating guide for JSFinder to extract URLs, routes, API paths, or subdomains from JavaScript assets.
---

# Tool Guide: JSFinder

## Overview

Use this skill when frontend JavaScript is likely to reveal hidden routes, APIs, subdomains, or internal references faster than blind fuzzing.

## When to Use

- The challenge hint mentions page loading, frontend logic, or hidden API routes.
- You already have HTML or JS assets and want to mine them for endpoints.
- You need quick URL and subdomain extraction from one page, one JS file, or a file list.

## Remote Path

- Script: `/root/niuniu-agent/tools/JSFinder/JSFinder.py`

## Recommended Workflow

1. Start with the exact entry page or JS asset you already know.
2. Use simple mode first.
3. Use deep mode only when the first page clearly loads more JS worth chasing.
4. Save extracted URLs and subdomains to files and fold the highest-signal candidates back into targeted testing.

## Practical Commands

Single page:

```bash
python3 /root/niuniu-agent/tools/JSFinder/JSFinder.py \
  -u http://target/ \
  -ou /tmp/jsfinder_urls.txt \
  -os /tmp/jsfinder_subdomains.txt
```

Deep mode:

```bash
python3 /root/niuniu-agent/tools/JSFinder/JSFinder.py \
  -u http://target/ \
  -d \
  -ou /tmp/jsfinder_urls.txt \
  -os /tmp/jsfinder_subdomains.txt
```

Analyze a list of JS URLs directly:

```bash
python3 /root/niuniu-agent/tools/JSFinder/JSFinder.py \
  -f /tmp/js_urls.txt \
  -j \
  -ou /tmp/jsfinder_urls.txt
```

## Operational Notes

- URLs must include `http://` or `https://`.
- Use `-c` when the page requires a session cookie.
- This is especially valuable for challenges like `2ihdUTWqg7iVcvvD7GAZzOadCxS` where page-loading logic may hide the next exploit surface.

## Resource Guardrails

- Do not deep-crawl indiscriminately if the page already exposes the key JS bundle names.
- Prefer extracting and triaging a smaller set of JS assets over recursively chasing everything.
