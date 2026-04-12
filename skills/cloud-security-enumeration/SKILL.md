---
name: cloud-security-enumeration
description: Use when a target may involve cloud assets, object storage, IAM exposure, metadata services, or AI infrastructure and you need cloudfox/cloud-oriented workflows.
---

# Cloud Security Enumeration

## Overview

Use this skill to map cloud identity, storage, compute, metadata, and AI-facing assets into an actionable attack surface.

## When to Use

- The target exposes cloud-hosted services, buckets, metadata, or IAM clues.
- You suspect temporary credentials, cloud misconfiguration, or AI control-plane exposure.
- A foothold may include cloud credentials or instance metadata access.

## Tool Selection

- `cloudfox`: fast situational awareness for cloud credentials and account structure.
- `nuclei`/`httpx`: external cloud asset triage and exposed management/API discovery.
- `curl`/custom scripts: metadata service checks and direct API validation.

## Quick Reference

1. Identify provider, account/project boundary, and exposed service types.
2. Check metadata, storage, identity, and public management surfaces.
3. Correlate any credentials with privilege and blast radius.
4. Record what is public, what is credential-gated, and what is worth escalating.

## Resource Guardrails

- Keep cloud enumeration scoped to the authorized account/project/tenant.
- Avoid noisy enumeration loops against large cloud inventories.
- Prefer read-only situational awareness until a deterministic next step exists.
