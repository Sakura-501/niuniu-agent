---
name: dependency-confusion-assessment
description: Use when a challenge may depend on package name collisions, private registry precedence, wildcard or unpinned dependencies, or mixed public-private package resolution paths.
---

# Dependency Confusion Assessment

## Overview

Use this skill when the attack path is likely a package name collision or registry-priority mistake.

## When to Use

- The target uses private package names, internal scopes, or mixed public/private registries.
- Manifests contain unpinned dependencies or installer-side references to internal package names.
- CI or build config pulls from multiple indexes without clear precedence guarantees.

## Quick Reference

1. Enumerate package names, scopes, index URLs, and resolver order.
2. Look for packages that appear internal but are not bound to a private scope or pinned source.
3. Identify whether public registries can satisfy names before the intended private source.
4. Confirm whether install-time code execution is possible through package hooks or build scripts.

## Helper Script

```bash
uv run python scripts/exploit_helpers/supplychain_manifest_triage.py requirements.txt package.json
```

## Common Mistakes

- Assuming every private-looking package name is actually protected by registry configuration.
- Ignoring `latest`, `*`, editable installs, or direct VCS refs because they are not package-name collisions.
- Forgetting that the real exploit often lands in install hooks or build scripts after resolution succeeds.
