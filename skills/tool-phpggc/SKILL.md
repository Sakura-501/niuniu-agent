---
name: tool-phpggc
description: Use when you need a practical operating guide for PHPGGC to generate PHP unserialize or PHAR gadget-chain payloads.
---

# Tool Guide: PHPGGC

## Overview

Use this skill when a PHP deserialization sink already exists and you need the shortest path to a fitting gadget chain.

## When to Use

- You have a confirmed PHP `unserialize()` or PHAR deserialization sink.
- You know or strongly suspect the target framework/library family.
- You need a gadget-chain generator faster than hand-building serialized payloads.

## Tool Location

- `phpggc`: `/root/niuniu-agent/tools/bin/phpggc`

## Recommended Workflow

1. Confirm the framework/library family and approximate version first.
2. List matching gadget chains and pick the smallest chain that fits the required vector.
3. Encode the payload for the real sink format instead of pasting raw serialized blobs blindly.
4. If the sink is PHAR-based, use PHAR output only after the file-operation path is confirmed.

## Practical Notes

- The wrapper uses the vendored upstream PHPGGC tree and requires `php` on the operator host.
- Prefer command generation only after you know whether the gadget wants command execution, PHP code, file write, or file read.
- Use wrapper/encoder options when the target blocks raw null bytes or expects base64/URL-encoded payloads.

## Example Patterns

```bash
phpggc -h
phpggc -l
```

## Resource Guardrails

- Do not guess gadget families without framework evidence.
- Keep generated payloads tied to the exact target stack and trigger vector.
