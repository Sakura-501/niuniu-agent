---
name: pivot_lateral
description: Multi-step pivot and lateral planning.
trigger_keywords: pivot, lateral, internal, foothold, next hop
recommended_tracks: track3, track4
usage_guidance: Track current foothold, next reachable segment, and credentials worth reusing.
---

# Pivot Lateral

Use this skill after you have an initial foothold and need the shortest path to the next environment or asset.

## Goals

- Maintain a clear map of foothold, reachable assets, and next-hop options.
- Avoid random movement that burns time without increasing privilege.
- Reuse existing access before generating new noise.

## Checklist

1. Record current user, host, network reachability, and available tools.
2. Identify the next most valuable reachable target.
3. Prefer credential reuse, trust relationships, or exposed management channels.
4. Keep notes of failed pivots to avoid loops.
