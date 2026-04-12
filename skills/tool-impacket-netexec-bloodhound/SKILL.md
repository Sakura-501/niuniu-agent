---
name: tool-impacket-netexec-bloodhound
description: Use when you need a practical operating guide for impacket, netexec, and bloodhound in Windows and AD environments.
---

# Tool Guide: impacket, netexec, and BloodHound

## Overview

Use this skill when internal Windows infrastructure is in play and you need a structured AD workflow.

## When to Use

- LDAP, SMB, Kerberos, WinRM, or DC clues appear.
- You have candidate credentials and need to validate or extend them.
- You need to map privilege paths rather than guessing the next hop.

## Recommended Workflow

1. Use `netexec` for fast credential validation and service reachability.
2. Use `impacket` for focused protocol actions, secrets extraction, or remote exec.
3. Use `bloodhound-python` only when graph collection is justified by the target state.
4. Keep the shortest privilege path as the planning anchor.

## Practical Notes

- Validate credentials quietly before broad collection.
- Use `kerbrute` only in controlled, scoped ways.
- Treat `mimikatz` as a Windows-side staged tool, not a Linux execution target.

## Resource Guardrails

- Avoid broad sweeps or spraying unless the expected value is clear.
- Large graph collection should be bounded to the current segment.
