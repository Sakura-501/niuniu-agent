---
name: tool-passthecert
description: Use when you need a practical operating guide for PassTheCert and Schannel-backed LDAP certificate authentication.
---

# Tool Guide: PassTheCert

## Overview

Use this skill when certificate material exists but PKINIT is unavailable or unreliable, and LDAP(S) over Schannel is the practical certificate-auth path.

## When to Use

- You have a certificate and private key for a domain identity.
- AD CS abuse or certificate theft already happened.
- PKINIT is unsupported or not the shortest path, but LDAPS is reachable.

## Tool Location

- `passthecert`: `/root/niuniu-agent/tools/bin/passthecert`

## Recommended Workflow

1. Confirm the cert/key pair, target DC, and LDAPS reachability.
2. Use `passthecert` to validate certificate-backed bind first.
3. Only then move into the intended LDAP action such as account modification, RBCD, or group membership changes.
4. Record the exact DC, cert subject, and LDAP action taken.

## Practical Notes

- The vendored wrapper runs the upstream Python script with `uv`, `impacket`, and `ldap3`.
- This is most useful after AD CS or certificate abuse, not as a blind first move.

## Example Patterns

```bash
passthecert -h
```

## Resource Guardrails

- Do not guess LDAP write actions before confirming the bind works.
- Keep certificate operations host-specific and do not mix cert/key pairs across identities.
