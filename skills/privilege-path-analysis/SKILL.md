---
name: privilege-path-analysis
description: Use when you already have execution on a system and need to identify realistic privilege-escalation or durable access paths from the current context.
---

# Privilege Path Analysis

## Overview

Use this skill to turn local execution into a ranked set of privilege paths instead of scattered checks.

## When to Use

- You already have a shell or command execution.
- Higher privilege or more durable access is likely required.
- The environment contains local privilege controls, secrets, or service accounts.

## Quick Reference

1. Enumerate sudo rules, capabilities, writable paths, services, and scheduled tasks.
2. Search for reusable credentials, tokens, keys, and local trust relationships.
3. Rank escalation paths by determinism and impact.
4. Keep notes on what was checked and what remains.

## Common Mistakes

- Repeating the same local checks every turn.
- Collecting credentials without tying them to a next step.
- Treating persistence as mandatory when simple privilege gain is enough.
