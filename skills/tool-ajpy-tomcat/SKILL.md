---
name: tool-ajpy-tomcat
description: Use when you need a practical operating guide for AJPy against Tomcat AJP connectors, including Ghostcat-style file reads and manager abuse.
---

# Tool Guide: AJPy for Tomcat AJP

## Overview

Use this skill when Tomcat AJP is exposed and you need focused AJP-native checks instead of generic HTTP fuzzing.

## When to Use

- Port `8009` or another AJP listener is reachable.
- The target fingerprints as Tomcat.
- You need AJP versioning, Ghostcat-style file reads, manager auth checks, or WAR deployment actions.

## Tool Location

- `ajpy-tomcat`: `/root/niuniu-agent/tools/bin/ajpy-tomcat`

## Recommended Workflow

1. Confirm AJP reachability and Tomcat fit first.
2. Start with version or file-read checks before any brute-force or WAR upload.
3. Use manager auth or deploy workflows only when the target clearly exposes that surface.
4. Save any valid manager creds, cookie, or readable internal file paths into notes immediately.

## Practical Notes

- The vendored wrapper runs the AJPy `tomcat.py` script directly with Python.
- `read_file` is the most direct Ghostcat/CVE-2020-1938 style primitive when the examples or app webroot context is known.

## Example Patterns

```bash
ajpy-tomcat -h
```

## Resource Guardrails

- Do not brute-force manager creds unless the AJP exposure is confirmed and the value is justified.
- Prefer single-file reads and narrow manager checks over repeated broad upload attempts.
