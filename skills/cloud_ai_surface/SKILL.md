---
name: cloud_ai_surface
description: Cloud and AI infrastructure discovery.
trigger_keywords: cloud, bucket, metadata, ai, model, inference, llm
recommended_tracks: track2
usage_guidance: Look for metadata endpoints, object storage, model APIs, and infra exposure.
---

# Cloud AI Surface

Use this skill when the target hints at cloud metadata, object storage, model serving, or AI infrastructure.

## Goals

- Identify cloud-only attack paths quickly.
- Separate application bugs from infrastructure exposure.
- Look for high-value secrets, tokens, and model control points.

## Checklist

1. Check for metadata services, signed URLs, and object storage references.
2. Look for model inference endpoints, prompt templates, and admin APIs.
3. Confirm whether the target can reach internal cloud or orchestration services.
4. Record exposed buckets, credentials, or model-control paths.
