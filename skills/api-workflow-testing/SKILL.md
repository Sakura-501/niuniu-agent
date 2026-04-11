---
name: api-workflow-testing
description: Use when a target is driven by JSON, REST, GraphQL, or token workflows and you need to compare request/response behavior across controlled API mutations.
---

# API Workflow Testing

## Overview

Use this skill to test structured APIs where request shape and authorization logic matter more than HTML rendering.

## When to Use

- The target exposes JSON or GraphQL endpoints.
- The interesting behavior sits in identifiers, tokens, methods, or hidden fields.
- You need to reason about workflow state transitions.

## Quick Reference

1. Capture the baseline request and response.
2. Mutate identifiers, role context, methods, or token state one at a time.
3. Watch for overbroad object access, hidden write paths, or missing authorization checks.
4. Keep the minimal working exploit sequence.

## Common Mistakes

- Ignoring baseline responses before changing inputs.
- Overlooking method changes such as `GET` versus `POST`.
- Treating empty arrays as proof that access control is working.
