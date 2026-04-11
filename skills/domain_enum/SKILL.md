---
name: domain_enum
description: Domain and Active Directory enumeration.
trigger_keywords: domain, ad, ldap, kerberos, dc, smb
recommended_tracks: track4
usage_guidance: Map domain roles, core hosts, and shortest escalation paths before action.
---

# Domain Enum

Use this skill when the environment looks like Active Directory or enterprise intranet infrastructure.

## Goals

- Identify domain controllers, users, trusts, and high-value servers.
- Turn fragmented host access into a domain graph.
- Prioritize the shortest path to privileged domain access.

## Checklist

1. Confirm domain membership, realm, DCs, and naming conventions.
2. Enumerate LDAP, SMB, Kerberos, shares, and key service accounts.
3. Record trust edges, admin paths, and credential reuse candidates.
4. Keep the map concise so later turns can reuse it.
