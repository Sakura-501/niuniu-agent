---
name: domain-operations
description: Use when Active Directory or Windows-centric enterprise infrastructure is involved and you need impacket, netexec, bloodhound, kerbrute, or credential operations.
---

# Domain Operations

## Overview

Use this skill to move from loose AD clues to a prioritized domain exploitation path.

## When to Use

- LDAP, Kerberos, SMB, WinRM, or DC signals are present.
- A foothold exposes domain credentials or internal Windows services.
- You need to map privilege paths, trust relationships, or remote execution surfaces.

## Tool Selection

- `impacket`: focused protocol operations, remote exec, secrets extraction, Kerberos workflows.
- `netexec`: fast credential validation and service reachability across Windows estates.
- `bloodhound-python`: graph-friendly privilege path collection.
- `kerbrute`: user enumeration and controlled password spraying.
- `mimikatz`: Windows-only credential extraction tool to stage or transfer when the target context permits.

## Quick Reference

1. Identify domain, DCs, reachable auth services, and any valid credentials.
2. Validate creds carefully before broadening scope.
3. Collect only the graph edges or secrets needed for the next step.
4. Rank lateral movement by shortest path to privileged access.

## Resource Guardrails

- Avoid broad password spraying or collection jobs without a concrete goal.
- Keep BloodHound/fscan/netexec sweeps bounded to the authorized network.
- Treat Windows-only tools as staged artifacts, not automatic first moves.
