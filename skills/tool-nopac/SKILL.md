---
name: tool-nopac
description: Use when you need a practical operating guide for noPac scanner or exploit workflows targeting CVE-2021-42278 and CVE-2021-42287.
---

# Tool Guide: noPac

## Overview

Use this skill when a domain scenario matches the noPac machine-account rename chain and you need either a quick vulnerable-path check or a concrete exploit runbook.

## When to Use

- AD target likely exposes the `CVE-2021-42278` + `CVE-2021-42287` chain.
- You have low-privileged domain credentials.
- `MachineAccountQuota`, `CreateChild`, or an editable computer account may make the chain viable.

## Tool Locations

- `nopac`: `/root/niuniu-agent/tools/bin/nopac`
- `nopac-scanner`: `/root/niuniu-agent/tools/bin/nopac-scanner`

## Recommended Workflow

1. Run the scanner or a bounded exploit attempt only after domain/DC identity is confirmed.
2. Check whether `MachineAccountQuota` or a reusable computer object is the likely path.
3. Prefer ticket/impersonation confirmation before adding shell or dump flags.
4. Record the DC host, chosen target computer object, and whether LDAP or LDAPS was required.

## Practical Notes

- The wrapper runs the vendored upstream Python implementation with `uv`, `impacket`, and `pyasn1`.
- The scanner is useful for quick fit checks before committing to the full exploit path.
- If SSL/LDAPS is unstable, the upstream guidance suggests retrying with LDAP when the environment requires it.

## Example Patterns

```bash
nopac-scanner -h
nopac -h
```

## Resource Guardrails

- Do not rename or reset arbitrary computer accounts without a clear rollback or disposable target.
- Stop if the environment does not clearly fit the noPac assumptions; do not brute-force this path.
