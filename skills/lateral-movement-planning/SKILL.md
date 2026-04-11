---
name: lateral-movement-planning
description: Use when you already have a foothold and need to choose the least wasteful next hop across hosts, services, trust edges, or internal segments.
---

# Lateral Movement Planning

## Overview

Use this skill to keep multi-step movement deliberate instead of exploratory noise.

## When to Use

- You have shell, credentials, or network position on one asset.
- More than one adjacent target is reachable.
- The challenge now depends on choosing the right next hop.

## Quick Reference

1. Record the current foothold, access level, network reachability, and available tools.
2. Rank reachable assets by likely value and effort.
3. Prefer credential reuse, trust edges, or management channels over brute force.
4. Preserve a short map of attempted and unattempted pivots.

## Common Mistakes

- Jumping to random hosts without recording reachability.
- Burning time on low-value neighbors.
- Forgetting why prior pivots failed.
