---
name: directory-identity-enumeration
description: Use when an environment appears to include centralized identity, directory, or trust infrastructure and you need a compact map of principals, core hosts, and relationships.
---

# Directory Identity Enumeration

## Overview

Use this skill to map identity infrastructure such as domains, LDAP, Kerberos, or shared trust systems.

## When to Use

- The target hints at domain membership, LDAP, Kerberos, or SMB trust.
- You need to understand principals, hosts, and relationships before moving further.
- Identity infrastructure is likely the shortest path to the next flag or privilege tier.

## Quick Reference

1. Confirm domain or realm identity and core controllers.
2. Enumerate principals, service accounts, key hosts, and shared resources.
3. Record trust relationships, role boundaries, and likely admin paths.
4. Keep the identity map short and reusable.

## Common Mistakes

- Treating identity data as background noise.
- Enumerating endlessly without building a usable graph.
- Ignoring which principals actually matter for escalation.
