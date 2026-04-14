---
name: tool-openssh-regresshion
description: Use when OpenSSH sshd banners, package versions, or race-condition clues suggest regreSSHion or CVE-2024-6387 and you need a practical operator guide for the local scanner or exploit helpers on the debug machine.
---

# Tool Guide: OpenSSH regreSSHion Helpers

## Overview

Use this skill when the target exposes SSH and there is a concrete reason to test `CVE-2024-6387` rather than doing generic SSH guessing. The debug machine currently has two local copies of the helper repo; both expose the Python PoC and the companion C source.

## When to Use

- The target banner fingerprints as OpenSSH and version clues are consistent with `CVE-2024-6387`.
- The host is reachable on `22/tcp` or another SSH port.
- You want a quick scanner first, then a narrow exploit attempt only if the version, platform, and race-condition assumptions fit.

## Tool Locations

- Primary repo: `/root/niuniu-agent/exp/CVE-2024-6387`
- Alternate repo: `/root/niuniu-agent/exp/openssh-exp-2`
- Python helper: `/root/niuniu-agent/exp/CVE-2024-6387/CVE-2024-6387.py`
- Alternate Python helper: `/root/niuniu-agent/exp/openssh-exp-2/CVE-2024-6387.py`
- Companion C source: `/root/niuniu-agent/exp/CVE-2024-6387/7etsuo-regreSSHion.c`
- Alternate C source: `/root/niuniu-agent/exp/openssh-exp-2/7etsuo-regreSSHion.c`

## Important Constraints

- The README in the vendored helper explicitly says the exploit path is only expected to work against **32-bit OpenSSH servers** because the PoC uses 32-bit pointer assumptions.
- Do not jump straight into exploit mode. Always confirm the SSH banner, version fit, and host reachability first.
- Treat these helpers as exploit-validation tools, not broad network scanners. Use `fscan` or a quick banner grab first, then hand the narrowed host list to this helper.

## Recommended Workflow

1. Confirm SSH reachability and capture the banner.
2. Use the Python helper in scan mode against a single host, a short target file, or a tight CIDR.
3. Only if the result still fits regreSSHion and the target looks like a compatible Linux/OpenSSH build, consider exploit mode.
4. If the PoC path requires a callback payload, start the listener first and verify it is reachable before the exploit attempt.
5. If exploit attempts do not fit the target architecture or banner, stop and pivot back to source, config, key, or credential extraction instead of hammering SSH.

## Practical Commands

Inspect helper usage:

```bash
cd /root/niuniu-agent/exp/CVE-2024-6387
python3 CVE-2024-6387.py -h
```

Scan a single SSH host:

```bash
cd /root/niuniu-agent/exp/CVE-2024-6387
python3 CVE-2024-6387.py scan -T 10.0.0.5 -p 22
```

Scan a short target list:

```bash
cd /root/niuniu-agent/exp/CVE-2024-6387
python3 CVE-2024-6387.py scan -T targets.txt -p 22 -o json -f regresshion-scan.json
```

Use the alternate helper's exploit-style syntax:

```bash
cd /root/niuniu-agent/exp/openssh-exp-2
python3 CVE-2024-6387.py --exploit 10.0.0.5 --port 22
```

Compile the companion C source if you need to inspect or adapt the payload logic:

```bash
cd /root/niuniu-agent/exp/CVE-2024-6387
gcc -shared -o exploit.so -fPIC 7etsuo-regreSSHion.c
```

## Practical Notes

- The two local directories are similar helper sets. Prefer `/root/niuniu-agent/exp/CVE-2024-6387` first, and fall back to `openssh-exp-2` if you specifically want its alternate CLI flow.
- `scan` mode is the default safe first step. Use it to validate banners and candidate targets before touching exploit mode.
- If you already have shell access on an adjacent host, run banner grabs from inside the environment first; that often gives better evidence than blind external probing.
- If the target is clearly 64-bit, patched, or heavily hardened, stop burning turns on regreSSHion and pivot to credential, key, config, or lateral-movement paths.

## Common Mistakes

- Trying exploit mode before confirming that the target is actually OpenSSH and plausibly vulnerable.
- Treating regreSSHion as a general-purpose SSH exploit against any OpenSSH banner.
- Repeating high-volume exploit attempts when the host architecture or version fit already looks wrong.
