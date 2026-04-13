---
name: ctf-core-knowledge
description: Use when a challenge may hinge on common CTF knowledge points, vulnerability families, exploitation patterns, or standard win-condition shortcuts across web, service, cloud, and internal targets.
---

# CTF Core Knowledge

## Overview

Use this skill when the challenge is less about one specific tool and more about recognizing the vulnerability class, common exploitation pattern, and shortest path to the flag.

## When to Use

- The target looks like a classic CTF web/service challenge.
- The next move depends on identifying the vulnerability family quickly.
- You need a compact checklist of common CTF pivots before wasting more scans.

## Common Knowledge Areas

### Web Vulnerability Families

- XSS
- SQL Injection
- Blind SQLi
- SSTI
- Command Injection
- GraphQL abuse
- IDOR / access-control gaps
- SSRF
- XXE
- LFI / file-read / traversal
- File upload chains
- Info disclosure
- Insecure deserialization
- HTTP smuggling / desync
- NoSQL injection
- Race conditions
- Business logic flaws

### Auth and Logic Shortcuts

- Default credentials
- Weak JWT validation
- Hidden role flags
- Password reset misuse
- Type juggling / weak comparison
- Path normalization bypass
- Header-based trust bypass
- Debug endpoints and backup artifacts

### Service / Network Patterns

- Open admin services on nonstandard ports
- Version leakage feeding CVE validation
- Redis / DB / internal panels exposed without proper auth
- Port-to-service mismatch
- Foothold to lateral movement through reachable internal services
- Telnet brute-force false positives caused by protocol negotiation

### Telnet Credential Verification Shortcut

If a telnet service reports a likely password spray hit, verify it with the bundled helper before trusting the result:

```bash
uv run python scripts/exploit_helpers/telnet_verify.py --host TARGET --port 23 --username USER --password PASS
```

This helper performs basic telnet IAC negotiation and checks whether the service actually accepts the credentials, which avoids hydra-style false positives.

### Cloud / AI / Infra Patterns

- Metadata access
- IAM / token abuse
- Bucket or object storage exposure
- Model-serving and inference API trust boundaries
- Public management APIs or misconfigured control-plane endpoints

### Internal / AD Patterns

- SMB share abuse
- Kerberos enumeration
- AD CS / certificate abuse
- Reusable credentials and tokens
- Service-account pivots
- Local privesc to domain impact

## Knowledge Point Playbooks

### 1. Default Credentials

#### Recognition Signals

- Login page or panel exists but no account provisioning flow is visible.
- Challenge text hints at a named user or test account.
- Source leakage or config exposure reveals hardcoded users.

#### Practical Method

1. Collect the exact login endpoint and session behavior.
2. Try the smallest set of likely defaults first:
   - challenge-provided pairs
   - `admin/admin`, `admin/password`, `test/test`, `user/password123`
3. Confirm success by session cookie, redirect, or role change.
4. After login, re-map the attack surface because hidden endpoints often appear post-auth.

#### Why It Matters

Default credentials are often not the flag by themselves; they unlock the real vulnerable sink such as a SOAP, admin, or file-management endpoint.

### 2. XXE / XML Parser Abuse

#### Recognition Signals

- SOAP or XML endpoints
- WSDL or XML-like request bodies
- File read symptoms inside XML fields
- Libraries like `lxml`, `DocumentBuilder`, `SAXParser`, or loose XML wrappers

#### Practical Method

1. Confirm the endpoint accepts user-controlled XML.
2. Start with a safe entity resolution probe.
3. If entities resolve, pivot to local file read:
   - target app config
   - source code
   - flag path
4. If local file read works, test whether response reflection gives you direct exfil.

#### Common Solution Pattern

The Xfenser SOAP benchmark writeup reinforces a very common chain:
- use default credentials to get a session
- identify the SOAP/XML endpoint
- inject a `DOCTYPE` with an external entity
- read the flag or source file through an XML field reflected in the response

### 3. Source / Backup File Enumeration

#### Recognition Signals

- Empty or odd endpoints like `/wsdl`, `/backup`, `/src`, `/static`
- Old-school servers returning `~`, `.bak`, `.swp`, `.old`, `.orig`
- Framework-specific source paths in predictable locations

#### Practical Method

1. Enumerate backup suffixes around known paths.
2. Prioritize code or config files over generic docs.
3. Once source is found, stop broad discovery and switch to code-driven exploit construction.

#### Why It Matters

Many “expert” CTF web chains are only solvable quickly once backup source reveals the exact gadget, callback, or hidden route.

### 4. PHP Deserialization / Gadget Chains

#### Recognition Signals

- Serialized cookies or session blobs like `O:<len>:"Class"...`
- Base64 or URL-encoded session tokens that decode to PHP object syntax
- Backup source reveals `__wakeup`, `__destruct`, `__get`, `__toString`, `call_user_func`

#### Practical Method

1. Decode the session/cookie first and identify the serialized object type.
2. Enumerate available classes from source or backups.
3. Trace all magic methods and data flow.
4. Search for dynamic invocation sinks:
   - `call_user_func`
   - file operations
   - command execution
   - dangerous include/require paths
5. Build the smallest gadget chain that reaches the sink.
6. If the payload fails, check language-specific serialization details before abandoning the path.

#### Common Solution Pattern

The Xfenser PortSwigger writeup reinforces several recurring lessons:
- backup source disclosure is often the pivot from “blind poking” to deterministic exploit building
- gadget-chain exploitation is mostly a call graph and object-shape problem
- subtle syntax details matter, especially private/protected property encoding

#### PHP-Specific Reminder

Private property serialization in PHP may require null-byte-prefixed names tied to the declaring class. If a custom gadget chain is “almost working”, inspect object encoding details before discarding the chain.

### 5. IDOR / Object Reference Abuse

#### Recognition Signals

- Numeric or UUID identifiers in requests
- “My data” endpoints that still accept arbitrary IDs
- Admin-only records accessible after auth

#### Practical Method

1. Capture one valid object request.
2. Change the object reference only.
3. Compare response shape, status, and leaked fields.
4. If access changes post-auth, test whether another role/user sees more data.

#### Why It Matters

In many CTFs the flag is hidden in another user’s record, not behind a full RCE chain.

### 6. Weak Comparison / Type Juggling

#### Recognition Signals

- PHP or loosely typed auth logic
- MD5/SHA hashes compared with `==` instead of strict checks
- Inputs or challenge text resembling `0e...`

#### Practical Method

1. Identify whether the check is numeric-string-like or loose boolean equality.
2. Search for values with magic-hash properties.
3. Test the smallest proof that flips the comparison branch.

#### Why It Matters

This is a classic CTF shortcut: no deep exploitation, just understanding how the runtime coerces values.

### 7. GraphQL Surface Abuse

#### Recognition Signals

- `/graphql`, `/graphiql`, introspection artifacts, or schema error messages
- Mutation names or object types visible in JS or traffic

#### Practical Method

1. Probe introspection or error messages to learn the schema shape.
2. Enumerate object and mutation names.
3. Test whether auth is enforced consistently across queries and mutations.
4. Focus on object ID swaps, hidden fields, and privileged mutation inputs.

### 8. Internal Service Pivoting

#### Recognition Signals

- One foothold reveals other hosts, internal URLs, or localhost-bound services
- Open proxy/tunnel paths
- Creds or tokens from one service are likely reusable elsewhere

#### Practical Method

1. Map what becomes reachable from the foothold.
2. Pick the shortest next-hop that is most likely to contain the flag.
3. Prefer tunnels or relays that directly enable the next service check.
4. Save route, credential, and cleanup data in notes/memory.

### 9. Local Privilege Escalation

#### Recognition Signals

- Shell exists but the flag path is inaccessible
- `sudo`, cron, writable services, capabilities, or process scheduling opportunities appear

#### Practical Method

1. Confirm user, groups, `sudo -l`, writable paths, and scheduled tasks.
2. Use `linpeas` or equivalent to collect high-signal clues.
3. Use `pspy` when timed execution or service behavior matters.
4. Rank paths before attempting exploitation.

## Benchmark-Informed Notes

The public Xfenser benchmark writeups reinforce several recurring benchmark truths:

- A small number of vulnerability families dominate real CTF-style pentest labs.
- The winning path is usually a chain of 2-3 crisp steps, not giant enumeration.
- Backup/source disclosure often turns a hard challenge into a deterministic exploit path.
- Post-auth attack surface changes are frequently more valuable than anonymous probing.
- If a path is very close to working, serialization, encoding, or parser semantics may be the missing detail rather than a wrong vulnerability family.

## Shortest-Path Heuristics

1. Prefer the vulnerability family that explains the fewest facts with the highest payoff.
2. Prefer one deterministic proof over broad noisy enumeration.
3. Prefer “flag-adjacent” sinks: file read, admin-only object, debug output, template render, command exec.
4. If the challenge is Jeopardy-style, ask what single trust boundary most likely protects the flag.
5. After any foothold, re-evaluate whether the flag is easier through local files, creds, or a nearby service than through deeper exploitation.

## Practical Challenge Checklist

- Is there a hidden route, file, or alternate handler?
- Is any parameter reflected in SQL, template, file path, or command context?
- Is there a role or object reference that can be swapped?
- Are there weak auth assumptions around JWT, cookies, headers, or local storage?
- Does the service banner/version point to a known exploit path?
- Is there a “too simple” value comparison, hashing, or encoding trick?
- Is the target better treated as a multi-step pivot challenge instead of a single-endpoint bug?

## Resource Guardrails

- Do not run every heavy tool just because the category list is broad.
- Use the category checklist to narrow the next experiment first.
- Summarize failed hypotheses explicitly so the agent does not re-try the same family.
