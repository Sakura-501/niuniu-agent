---
name: flag_submit_recovery
description: Flag submission and follow-up recovery handling.
trigger_keywords: flag, submit, retry, recovery
recommended_tracks: track1, track2, track3, track4
usage_guidance: Submit candidate flags immediately and use result feedback to decide next step.
---

# Flag Submit Recovery

Use this skill when a candidate flag appears or when the current path failed and needs controlled recovery.

## Goals

- Submit promising flags immediately.
- Convert submit responses into state updates.
- Continue from known evidence instead of restarting blindly.

## Checklist

1. Validate the candidate artifact shape and origin.
2. Submit immediately once confidence is reasonable.
3. If accepted or already solved, sync notes and stop the finished instance.
4. If rejected, record the exact feedback and choose the smallest next branch.
