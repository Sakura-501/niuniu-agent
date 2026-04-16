---
name: flag-discovery-and-submission
description: Use when a service has been compromised or a file-read primitive exists and flags may be stored on disk, in databases, caches, configs, or responses.
---

# Flag Discovery and Submission

## Overview

Use this once any service is compromised. A service instance commonly has at least one local flag or nearby secret.

## Search Order

1. Read obvious files: `/challenge/flag.txt`, `/challenge/flag1.txt`, `/challenge/flag2.txt`, `/flag`, `/flag.txt`.
2. Search service roots: `/var/www`, app directory, upload directory, working directory.
3. Search configs, logs, database dumps, Redis keys, and backup files.
4. Expand only if needed: limited filesystem `find`, then targeted `grep`.

## Commands

```bash
find /challenge /app /var/www /tmp -maxdepth 5 -type f \\( -iname 'flag*' -o -iname '*flag*.txt' \\) 2>/dev/null
grep -R --binary-files=without-match -E 'flag\\{[^}]{6,}\\}' /challenge /app /var/www 2>/dev/null | head -n 50
```

## Submission Rule

- If a string matches `flag{...}`, call `submit_flag` immediately, even if it may have been submitted before.
- In multi-flag challenges, keep going after one flag until official completion or timeout.
