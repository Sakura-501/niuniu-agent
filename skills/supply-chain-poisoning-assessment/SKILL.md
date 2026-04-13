---
name: supply-chain-poisoning-assessment
description: Use when a target challenge involves package managers, manifests, CI pipelines, private registries, build steps, or dependency ingestion and you need a focused workflow for supply-chain poisoning and trust-boundary abuse.
---

# Supply-Chain Poisoning Assessment

## Overview

Use this skill when the shortest path is through build-time trust, dependency resolution, registry confusion, or installer-side code execution rather than direct application exploitation.

## When to Use

- The challenge exposes `requirements.txt`, `package.json`, CI workflows, package registries, or build scripts.
- Notes or hints mention dependency confusion, malicious packages, CI poisoning, untrusted artifacts, or manifest abuse.
- You need to triage trust boundaries around package resolution and installer execution.

## Quick Reference

1. Identify the package ecosystem: pip, npm, pnpm, yarn, Poetry, uv, GitHub Actions, or custom registry.
2. Triage manifests for direct URLs, VCS refs, editable installs, wildcard specs, private scope usage, and install hooks.
3. Inspect workflows for unpinned actions, remote script execution, and artifact trust assumptions.
4. Confirm whether the exploit path is dependency confusion, malicious update, install-hook execution, or workflow poisoning.

## Helper Scripts

```bash
uv run python scripts/exploit_helpers/supplychain_manifest_triage.py requirements.txt package.json
uv run python scripts/exploit_helpers/workflow_risk_scan.py .github/workflows/*.yml
```

## Common Mistakes

- Treating supply-chain challenges like normal web apps and missing the build/install path.
- Ignoring install hooks and CI actions after identifying a manifest.
- Testing registry confusion before confirming package naming, source priority, or private scope behavior.
