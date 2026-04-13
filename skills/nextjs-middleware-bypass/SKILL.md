---
name: nextjs-middleware-bypass
description: Use when a target is protected by self-hosted Next.js Middleware and you need a concrete playbook for auth bypass checks, especially around the x-middleware-subrequest family of protections.
---

# Next.js Middleware Bypass

## Overview

Use this skill when a self-hosted Next.js target appears to rely on Middleware for access control and routing decisions. The highest-value concrete check is `CVE-2025-29927`.

## When to Use

- Redirects or auth checks look Middleware-driven.
- The app is clearly self-hosted Next.js rather than Vercel-managed routing.
- Protected routes differ mainly by redirect behavior rather than backend authorization failures.

## Concrete CVE Lead

- `CVE-2025-29927`:
  Older self-hosted Next.js builds could be coerced into skipping Middleware via crafted `x-middleware-subrequest` request headers. The exploit check is simple: replay the baseline request to a protected route, then add the header variants and look for a redirect-to-200 or redirect-to-different-behavior transition.

## Exploit Playbook

1. Capture the baseline request to a protected route and note status, redirect target, cookies, and response length.
2. Replay with candidate `x-middleware-subrequest` values and compare behavior one variable at a time.
3. If the route becomes reachable, immediately test whether the backend route itself still enforces auth or whether the protection was Middleware-only.
4. Only treat it as a true bypass if the protected content or state-changing route is usable after the header mutation.

## Common Mistakes

- Testing only one header value and concluding the target is safe.
- Calling it a bypass when the backend still rejects unauthenticated access.
- Forgetting that this is mainly relevant to self-hosted deployments.
