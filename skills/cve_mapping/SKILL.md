---
name: cve_mapping
description: Map versions and fingerprints to likely CVEs.
trigger_keywords: cve, version, apache, nginx, spring, grafana, fastapi
recommended_tracks: track2
usage_guidance: Identify component and version first, then rank likely exploit candidates.
---

# CVE Mapping

Use this skill when you already have a product fingerprint, version clue, or clear framework signature.

## Goals

- Convert vague banners into ranked exploit candidates.
- Focus on realistic CVEs with matching prerequisites.
- Prefer deterministic exploit paths over speculative fuzzing.

## Checklist

1. Normalize product, version, and deployment clues.
2. Filter to CVEs that match the observed version window.
3. Confirm exploit preconditions such as auth state, plugin presence, or filesystem access.
4. Rank the shortest likely path to flag-bearing impact.
