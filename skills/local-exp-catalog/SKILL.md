---
name: local-exp-catalog
description: Use when local exploit references, PoC scripts, or product-specific notes may already exist under the repository exp directory and you want to reuse them before external research or ad-hoc payload building.
---

# Local EXP Catalog

## Overview

Use this skill when the repository already contains product/CVE-specific exploit notes or PoC files under the local EXP catalog and you want to reuse them first.

## When to Use

- The challenge has a known product or CVE hint.
- The debug machine has the repository checked out under `/root/niuniu-agent`.
- You want to avoid re-deriving public exploit setup from scratch.

## Quick Reference

1. Check `/root/niuniu-agent/exp` for matching CVE or product folders.
2. Read the local `README.md` or note file before using the PoC.
3. Prefer adapting the local exploit reference to the current target over downloading a fresh copy during the round.
4. Record which local PoC path was useful in challenge memory.

## Common Mistakes

- Ignoring a local PoC directory and redoing internet research.
- Running an exploit script without first checking product/version fit.
- Forgetting to write the exact local PoC path back into persistent challenge memory.
