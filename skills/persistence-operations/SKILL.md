---
name: persistence-operations
description: Use when temporary access must be preserved carefully using tunnels, service relays, credentials, or low-noise foothold recovery paths.
---

# Persistence Operations

## Overview

Use this skill to preserve access just enough for the mission without creating unnecessary noise or complexity.

## When to Use

- A valid foothold may be lost before the next phase completes.
- The environment is unstable or challenge infrastructure resets often.
- You need to preserve a route for follow-on enumeration or submission.

## Quick Reference

1. Decide whether persistence is actually needed or whether simple note-taking is enough.
2. Prefer reversible, challenge-appropriate persistence such as saved credentials or a lightweight tunnel.
3. Record every persistence mechanism and how to clean it up.
4. Recheck whether the objective is still active before maintaining more access.

## Common Mistakes

- Treating persistence as mandatory when a repeatable exploit already exists.
- Leaving orphan tunnels and listeners after the next step changes.
- Forgetting to save credential location, port mapping, or cleanup procedure.
