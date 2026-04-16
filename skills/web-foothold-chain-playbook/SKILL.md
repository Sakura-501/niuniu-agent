---
name: web-foothold-chain-playbook
description: Use when a web target may lead from upload, LFI, SSRF, SQLi, SSTI, deserialization, or auth bypass to command execution or file-read impact.
---

# Web Foothold Chain Playbook

## Overview

Use this to convert a web bug into a reproducible foothold. Prefer deterministic chains over broad fuzzing.

## Common Chains

- Upload bypass: login or weak auth -> upload extension/content-type bypass -> webshell -> `id`, `pwd`, `ip a`, flag search.
- LFI: path normalization bypass -> source/config/session read -> `pearcmd.php`, log poison, session hijack, or credentials.
- SSRF: internal HTTP probe -> local source/config read -> admin API, metadata, or internal database pivot.
- SQLi: confirm injectable parameter -> read users/config -> `INTO OUTFILE` only if writable path is proven.
- SSTI/deserialization: fingerprint template/runtime -> one benign command marker -> controlled RCE.

## Minimum Evidence

For every step keep:

- exact URL or request
- expected marker such as `uid=`, file content, or response difference
- recovered credential/session/token
- flag candidate submitted immediately

## Example Flow

```bash
curl -i http://target/login.php
curl -s 'http://target/proxy.php?url=file:///etc/passwd'
curl -sG --data-urlencode 'cmd=id' 'http://target/uploads/shell.php'
```

## Common Mistakes

- Treating a `200 OK` homepage as RCE success.
- Reusing a webshell path from an old container without revalidating it.
- Continuing content discovery after a proven file-read or command primitive appears.
