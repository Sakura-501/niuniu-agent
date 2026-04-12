---
name: ctf-core-knowledge
description: Use when a challenge may hinge on common CTF knowledge points, vulnerability families, exploitation patterns, or standard win-condition shortcuts across web, service, cloud, and internal targets.
---

# CTF Core Knowledge

## Overview

Use this skill when the challenge is less about one specific tool and more about recognizing the vulnerability class, common exploitation pattern, and shortest path to the flag.

## When to Use

- The target looks like a classic CTF web/service challenge.
- The next move depends on identifying the vulnerability family quickly.
- You need a compact checklist of common CTF pivots before wasting more scans.

## Common Knowledge Areas

### Web Vulnerability Families

- XSS
- SQL Injection
- Blind SQLi
- SSTI
- Command Injection
- GraphQL abuse
- IDOR / access-control gaps
- SSRF
- XXE
- LFI / file-read / traversal
- File upload chains
- Info disclosure
- Insecure deserialization
- HTTP smuggling / desync
- NoSQL injection
- Race conditions
- Business logic flaws

### Auth and Logic Shortcuts

- Default credentials
- Weak JWT validation
- Hidden role flags
- Password reset misuse
- Type juggling / weak comparison
- Path normalization bypass
- Header-based trust bypass
- Debug endpoints and backup artifacts

### Service / Network Patterns

- Open admin services on nonstandard ports
- Version leakage feeding CVE validation
- Redis / DB / internal panels exposed without proper auth
- Port-to-service mismatch
- Foothold to lateral movement through reachable internal services

### Cloud / AI / Infra Patterns

- Metadata access
- IAM / token abuse
- Bucket or object storage exposure
- Model-serving and inference API trust boundaries
- Public management APIs or misconfigured control-plane endpoints

### Internal / AD Patterns

- SMB share abuse
- Kerberos enumeration
- AD CS / certificate abuse
- Reusable credentials and tokens
- Service-account pivots
- Local privesc to domain impact

## Shortest-Path Heuristics

1. Prefer the vulnerability family that explains the fewest facts with the highest payoff.
2. Prefer one deterministic proof over broad noisy enumeration.
3. Prefer “flag-adjacent” sinks: file read, admin-only object, debug output, template render, command exec.
4. If the challenge is Jeopardy-style, ask what single trust boundary most likely protects the flag.
5. After any foothold, re-evaluate whether the flag is easier through local files, creds, or a nearby service than through deeper exploitation.

## Practical Challenge Checklist

- Is there a hidden route, file, or alternate handler?
- Is any parameter reflected in SQL, template, file path, or command context?
- Is there a role or object reference that can be swapped?
- Are there weak auth assumptions around JWT, cookies, headers, or local storage?
- Does the service banner/version point to a known exploit path?
- Is there a “too simple” value comparison, hashing, or encoding trick?
- Is the target better treated as a multi-step pivot challenge instead of a single-endpoint bug?

## Resource Guardrails

- Do not run every heavy tool just because the category list is broad.
- Use the category checklist to narrow the next experiment first.
- Summarize failed hypotheses explicitly so the agent does not re-try the same family.
