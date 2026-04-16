---
name: credential-secret-hunting
description: Use when a foothold, file-read, source disclosure, Redis, database, session, or config leak may contain credentials or reusable secrets.
---

# Credential and Secret Hunting

## Overview

Use this whenever a foothold or file-read exists. The fastest next flag is often in config, sessions, cache, or database rows.

## Search Order

1. Local app files: `.env`, `config.php`, `settings.py`, `database.yml`, `application.properties`, `docker-compose.yml`.
2. Runtime state: `/proc/self/environ`, session directories, upload directories, logs, backup files.
3. Datastores: Redis keys, MariaDB/PostgreSQL users/config tables, SQLite files.
4. Framework secrets: Flask `SECRET_KEY`, Django `SECRET_KEY`, JWT keys, signing salts, API tokens.
5. Reuse carefully: only apply credentials to services supported by evidence.

## Commands

```bash
grep -R --line-number -Ei 'password|passwd|secret|token|apikey|dsn|mysql|redis|flag\\{' /var/www 2>/dev/null | head -n 80
find / -maxdepth 4 -type f \\( -name '.env' -o -iname '*config*' -o -iname '*.sqlite*' -o -iname '*backup*' \\) 2>/dev/null
redis-cli -h HOST -a 'PASSWORD' --no-auth-warning keys '*'
mysql -h HOST -uroot -proot -e 'show databases;'
```

## Notes

- Submit any `flag{...}` immediately.
- Save exact credential source and target service.
- Do not brute-force before exhausting config/session/datastore sources.
