---
name: redis-mariadb-lateral-movement
description: Use when a foothold reveals internal Redis, MariaDB, or PostgreSQL services and you need a focused workflow for service triage, credential hunting, and internal pivot decisions.
---

# Redis / MariaDB Lateral Movement

## Overview

Use this skill when internal service discovery finds Redis, MariaDB, or PostgreSQL and you need to decide whether the next move is direct auth, credential extraction, config theft, or further pivoting.

## When to Use

- A foothold already exists and internal ports like `6379`, `3306`, or `5432` are visible.
- The challenge notes mention Redis, MariaDB, internal OA, or database-backed apps.
- You need a quick internal service map before trying auth or dumping secrets.

## Quick Reference

1. Triage reachability first:

```bash
uv run python scripts/exploit_helpers/internal_service_triage.py --host 172.19.0.3
```

2. For Redis:
   - test unauth first
   - inspect `INFO`, config paths, keys, and app secrets
3. For MariaDB/PostgreSQL:
   - look for credentials in app configs, PHP sessions, env files, and ORM settings
   - use the DB as a secret store and host inventory source
4. Record the exact host, auth state, and next credential hypothesis before moving on.

## Common Mistakes

- Jumping straight to brute force instead of checking app config or session artifacts.
- Treating an open Redis/MySQL port as enough proof of exploitability.
- Forgetting that the value may be secrets and pivot data, not only raw command execution.
