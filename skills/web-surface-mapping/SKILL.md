---
name: web-surface-mapping
description: Use when a target exposes web entrypoints and the next step is to map routes, parameters, linked assets, and framework clues before deeper testing.
---

# Web Surface Mapping

## Overview

Use this skill to turn a vague HTTP entrypoint into a compact, reusable attack surface map.

## When to Use

- Root page or login page is reachable.
- A challenge looks web-first but the useful paths are not obvious yet.
- You need enough structure to choose the next exploit path without brute force.

## Quick Reference

1. Fetch the root page and note technologies, forms, links, and embedded scripts.
2. Check obvious discovery endpoints such as `robots.txt`, docs, OpenAPI, health checks, and static assets.
3. Compare response shapes, status codes, and content types for candidate paths.
4. Record route patterns, parameters, auth gates, and framework hints.

## Common Mistakes

- Jumping into exploitation before confirming the real request shape.
- Treating every `404` path as equally meaningful.
- Losing the route map after the next step starts.
