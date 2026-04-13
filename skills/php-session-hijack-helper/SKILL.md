---
name: php-session-hijack-helper
description: Use when a foothold exposes PHP session files under /tmp or similar paths and you need a fast way to extract admin, CSRF, or role values from PHP session blobs.
---

# PHP Session Hijack Helper

## Overview

Use this skill when the target stores useful state in PHP session files and you want a quick parser instead of manually decoding raw `sess_*` contents.

## Quick Reference

```bash
uv run python scripts/exploit_helpers/php_session_hijack_helper.py /tmp/sess_abcd1234
```

Use the output to identify:
- admin role markers
- CSRF tokens
- usernames and session-bound workflow values

## Common Mistakes

- Treating the session blob as opaque text and missing easy admin tokens.
- Reusing a session without checking which cookie name or path the app expects.
