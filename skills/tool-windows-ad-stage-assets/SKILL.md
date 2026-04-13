---
name: tool-windows-ad-stage-assets
description: Use when a Windows foothold needs staged AD or local escalation assets such as Powermad, PrivescCheck, Certify, Rubeus, SharpHound, SweetPotato, or legacy Kerberos tooling.
---

# Tool Guide: Windows AD Stage Assets

## Overview

Use this skill when the operator host already has a Windows foothold or upload path and you need pre-staged scripts or binaries for domain abuse or local privilege-escalation work.

## When to Use

- You already have a Windows foothold or reliable file-transfer path.
- Linux-native tooling is no longer enough by itself.
- You need a known Windows-side script or binary instead of improvising one.

## Asset Locations

- `powermad-asset`: `/root/niuniu-agent/tools/bin/powermad-asset`
- `privesccheck-asset`: `/root/niuniu-agent/tools/bin/privesccheck-asset`
- `certify-asset`: `/root/niuniu-agent/tools/bin/certify-asset`
- `ms14-068-asset`: `/root/niuniu-agent/tools/bin/ms14-068-asset`
- `rubeus-asset`: `/root/niuniu-agent/tools/bin/rubeus-asset`
- `sharphound-asset`: `/root/niuniu-agent/tools/bin/sharphound-asset`
- `sweetpotato-asset`: `/root/niuniu-agent/tools/bin/sweetpotato-asset`
- `sebackupprivilege-asset`: `/root/niuniu-agent/tools/bin/sebackupprivilege-asset`

## Recommended Workflow

1. Confirm target OS, privileges, architecture, and transfer method.
2. Stage only the single asset that answers the current hypothesis.
3. Run the asset on the Windows foothold, not on the Linux operator host.
4. Save findings or generated credentials into notes and memory instead of giant raw dumps.

## Practical Notes

- `Powermad.ps1`: useful for `MachineAccountQuota` and ADIDNS abuse chains.
- `PrivescCheck.ps1`: useful for fast Windows local privilege-escalation triage.
- `Certify.exe`: useful for AD CS enumeration/request paths from a Windows foothold.
- `Rubeus.exe`: useful for Kerberos ticket requests, roast paths, and delegated auth workflows from a Windows foothold.
- `SharpHound.exe`: useful when Windows-side BloodHound collection is faster or more complete than Linux collection alone.
- `SweetPotato.exe`: useful for Windows service-account to SYSTEM privilege-escalation attempts when the environment fits potato-style abuse.
- `SeBackupPrivilege` DLLs: useful when the foothold has `SeBackupPrivilege` and you need to copy protected files such as `SAM`, `SYSTEM`, `SECURITY`, or `ntds.dit`.
- `MS14-068.exe`: legacy Kerberos tooling; only use when the environment clearly matches that old path.

## Example Patterns

```bash
powermad-asset
privesccheck-asset
certify-asset
rubeus-asset
sharphound-asset
sweetpotato-asset
sebackupprivilege-asset
ms14-068-asset
```

The commands above print the staged asset path on the operator host so you can upload or reference it explicitly.

## Resource Guardrails

- Do not upload multiple large Windows assets unless each one answers a different hypothesis.
- Treat `MS14-068.exe` as legacy-only; prefer current AD CS, coercion, delegation, and certificate paths first.
