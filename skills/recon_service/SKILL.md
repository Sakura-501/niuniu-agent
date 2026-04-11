---
name: recon_service
description: Service and protocol discovery for non-pure-web targets.
trigger_keywords: service, port, tcp, udp, ssh, redis, mysql, fastapi
recommended_tracks: track1, track2, track3, track4
usage_guidance: Enumerate ports, service banners, and versions before choosing exploit paths.
---

# Recon Service

Use this skill when the target may expose multiple services or when web is not the only entrypoint.

## Goals

- Confirm the real service surface before choosing exploit tools.
- Distinguish management ports from user-facing ports.
- Capture product/version fingerprints that can feed CVE mapping.

## Checklist

1. Enumerate open ports and protocol banners.
2. Check for common management ports such as SSH, SMB, LDAP, Redis, MySQL, and RDP.
3. Validate whether the service is reachable directly or only through a foothold.
4. Record version strings, TLS details, and access restrictions.
