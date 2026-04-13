---
name: ci-workflow-poisoning
description: Use when a challenge revolves around CI or automation trust, such as unpinned GitHub Actions, artifact reuse, remote install scripts, or workflow-driven package poisoning.
---

# CI Workflow Poisoning

## Overview

Use this skill when the attack surface is the pipeline itself rather than the deployed app.

## When to Use

- The target includes GitHub Actions, GitLab CI, Jenkinsfiles, or other pipeline definitions.
- You see reusable workflows, action pins by tag, remote script execution, or artifact handoff between jobs.
- Package installs or deployment steps happen inside CI and may trust unverified sources.

## Quick Reference

1. Extract all `uses:` references and check whether they are pinned to immutable SHAs.
2. Flag remote script execution, dynamic installers, and artifact reuse across trust boundaries.
3. Trace where secrets become available and which steps can influence code before that point.
4. Separate “build poisoning” from “runtime exploitation”; CI challenges often end before deployment.

## Helper Script

```bash
uv run python scripts/exploit_helpers/workflow_risk_scan.py .github/workflows/*.yml
```

## Common Mistakes

- Treating any tagged action as pinned.
- Ignoring artifact reuse and only looking at install commands.
- Missing the exact step where a low-trust input becomes high-trust code.
