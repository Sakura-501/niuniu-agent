---
name: pearcmd-php-shell-drop
description: Use when a challenge already has PHP local file inclusion or path traversal and you need a fast pearcmd.php command-generation path to drop a controllable PHP file.
---

# PEARCMD PHP Shell Drop

## Overview

Use this skill when you already have PHP LFI and the target ships PEAR. The main goal is to generate the right `pearcmd.php` argument payload quickly and stop wasting time hand-encoding it.

## When to Use

- LFI to local PHP files is already confirmed.
- `pearcmd.php` or PEAR paths are reachable from the include sink.
- The challenge wants a fast foothold rather than deep version-specific exploitation.

## Quick Reference

1. Confirm LFI first.
2. Generate the PEAR payload locally:

```bash
uv run python scripts/exploit_helpers/pearcmd_payload.py --webshell-path /tmp/sh.php
```

3. Feed the encoded payload into the vulnerable include path and confirm the file lands.
4. Replace the first-stage shell with a cleaner second-stage webshell if needed.

## Common Mistakes

- Trying PEAR before proving LFI.
- Hand-encoding long PEAR payloads and introducing quoting errors.
- Stopping after the first shell without stabilizing the foothold.
