---
name: cloud-asset-assessment
description: Use when a target hints at cloud metadata, object storage, model serving, or infrastructure control points and you need to map exposed assets before exploitation.
---

# Cloud Asset Assessment

## Overview

Use this skill to separate application behavior from exposed cloud or AI infrastructure.

## When to Use

- Responses reveal buckets, metadata, model APIs, or infrastructure identifiers.
- The environment may include managed storage or model-serving endpoints.
- You need to identify high-value secrets and control surfaces quickly.

## Quick Reference

1. Check for metadata endpoints, signed URLs, and object storage references.
2. Enumerate model-serving or inference APIs if present.
3. Confirm whether the target can reach internal cloud services.
4. Record high-value assets, secrets, and infrastructure control points.

## Common Mistakes

- Treating cloud references as mere strings without probing trust boundaries.
- Focusing only on the app layer when infra clues are already visible.
- Failing to record which assets are externally reachable versus internal-only.
