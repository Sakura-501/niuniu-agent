---
name: proxy-php-ssrf-lfi-helper
description: Use when a challenge exposes a proxy.php style fetch endpoint and you need a fast helper to generate SSRF or file:// probe URLs for internal hosts and local file reads.
---

# proxy.php SSRF / LFI Helper

## Overview

Use this skill when the challenge has a `proxy.php?url=` style primitive and you want to pivot quickly into internal HTTP or local file targets.

## Quick Reference

```bash
uv run python scripts/exploit_helpers/proxy_php_ssrf_lfi_helper.py --base-url http://TARGET file:///etc/passwd http://172.20.0.3:8080/
```

This gives ready-to-use probe URLs for:
- local file reads
- internal web reachability
- loopback services

## Common Mistakes

- Hand-building long SSRF URLs and introducing encoding errors.
- Only using `http://` targets and forgetting `file://` for source reads.
- Not recording which internal hosts responded for the next stage.
