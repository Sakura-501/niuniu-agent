---
name: ad-internal-compromise-flow
description: Use when internal Windows, SMB, LDAP, Kerberos, AD CS, domain controller, WinRM, or credential material appears during a penetration test.
---

# AD Internal Compromise Flow

## Overview

Use this when the environment looks like Windows/AD. Minimize noisy brute force and build from valid identity evidence.

## Flow

1. Fingerprint domain services: DNS, LDAP, Kerberos, SMB, WinRM, MSSQL, AD CS.
2. Validate known credentials once with low-noise tools.
3. Enumerate SMB shares, users, groups, SPNs, local admins, and AD CS templates.
4. If credentials work, collect graph edges with BloodHound/SharpHound only as needed.
5. Try Kerberoast, AS-REP roast, weak shares, writable paths, service config leaks, AD CS ESC paths.
6. For Windows footholds, stage only necessary assets: winPEAS, SharpHound, Rubeus, Mimikatz, Certify.

## Commands

```bash
netexec smb 10.0.0.0/24 -u USER -p PASS --shares
kerbrute userenum -d DOMAIN users.txt --dc DC_IP
certipy find -u USER -p PASS -dc-ip DC_IP -target DOMAIN -vulnerable
bloodhound-python -u USER -p PASS -d DOMAIN -ns DC_IP -c DCOnly
```

## Guardrails

- Do not spray passwords without evidence.
- Keep credential source, tested target, and result in notes.
- Prefer read-only enumeration until a concrete privilege path appears.
