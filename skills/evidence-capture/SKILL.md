---
name: evidence-capture
description: Use when an action produced useful evidence, a candidate flag, or an ambiguous result and the next step is to capture, submit, or branch cleanly without losing context.
---

# Evidence Capture

## Overview

Use this skill to keep useful artifacts from being lost during fast iteration.

## When to Use

- A request exposed sensitive data or a candidate flag.
- A result is promising but still needs submission or comparison.
- Recovery depends on preserving exactly what happened.

## Quick Reference

1. Record the minimal artifact set: request, payload, response, and local notes.
2. Submit candidate flags as soon as confidence is reasonable.
3. Use the submit result to decide whether to stop, continue, or branch.
4. Keep recovery notes short enough for the next turn to reuse immediately.

## Common Mistakes

- Discovering a useful artifact and not recording the path that found it.
- Delaying submission until the context is gone.
- Letting recovery notes become noisy transcripts instead of decision support.
