---
name: tool-kerbrute-smb-enum
description: Use when you need a practical operating guide for kerbrute, smbmap, enum4linux-ng, and responder-style SMB/identity enumeration.
---

# Tool Guide: kerbrute, smbmap, enum4linux-ng, responder

## Overview

Use this skill when AD or Windows file services are involved and you need quick auth and share visibility.

## When to Use

- SMB, NetBIOS, LDAP, or Kerberos is exposed.
- You need to validate users, shares, or relay opportunities.
- You need quick Windows-side reconnaissance before broader AD collection.

## Recommended Workflow

1. Use `kerbrute` for bounded user enumeration or careful password validation.
2. Use `smbmap` for share and permission visibility.
3. Use `enum4linux-ng` for SMB/NetBIOS enumeration when Linux-side coverage is needed.
4. Use `responder` only when the scenario actually supports poisoning/relay style opportunities.

## Resource Guardrails

- Keep sprays bounded and justified.
- Do not leave poisoning tools active without a concrete goal and cleanup plan.
