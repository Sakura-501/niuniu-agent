from __future__ import annotations

import json
import re
from typing import Any


RISKY_INSTALL_HOOKS = ("preinstall", "install", "postinstall", "prepare", "prepublish", "prepublishOnly")


def triage_python_requirements(text: str) -> dict[str, Any]:
    direct_urls: list[str] = []
    editable: list[str] = []
    vcs_refs: list[str] = []
    unpinned: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if any(marker in line for marker in ("git+", "hg+", "svn+", "bzr+")):
            vcs_refs.append(line)
        if line.startswith("-e ") or line.startswith("--editable"):
            editable.append(line)
            continue
        if "://" in line or "@ http" in line:
            direct_urls.append(line)
        if re.match(r"^[A-Za-z0-9_.-]+(\[[^]]+\])?$", line):
            unpinned.append(line)

    return {
        "direct_urls": direct_urls,
        "editable": editable,
        "vcs_refs": vcs_refs,
        "unpinned": unpinned,
    }


def triage_package_json(text: str) -> dict[str, Any]:
    data = json.loads(text)
    scripts = data.get("scripts") or {}
    risky_scripts = {name: body for name, body in scripts.items() if name in RISKY_INSTALL_HOOKS}

    dependencies: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        dependencies.update(data.get(key) or {})

    direct_sources = {
        name: version
        for name, version in dependencies.items()
        if any(token in str(version) for token in ("git+", "github:", "http://", "https://", "file:", "link:", "workspace:"))
    }
    unpinned = {
        name: version
        for name, version in dependencies.items()
        if str(version).strip() in {"*", "latest"} or re.match(r"^[~^]?\d+$", str(version).strip())
    }

    return {
        "name": data.get("name"),
        "risky_install_scripts": risky_scripts,
        "direct_dependency_sources": direct_sources,
        "loose_dependency_specs": unpinned,
        "has_overrides": bool(data.get("overrides")),
        "has_resolutions": bool(data.get("resolutions")),
    }


def triage_workflow_yaml(text: str) -> dict[str, Any]:
    unpinned_actions = re.findall(r"uses:\s*([^\s@]+@[^\s]+)", text)
    unpinned_actions = [item for item in unpinned_actions if not re.search(r"@[0-9a-f]{40}$", item)]
    dangerous_steps = [
        line.strip()
        for line in text.splitlines()
        if any(token in line for token in ("curl ", "wget ", "bash -c", "| bash", "pip install", "npm install", "pnpm install", "yarn install"))
    ]
    return {
        "unpinned_actions": unpinned_actions,
        "dangerous_steps": dangerous_steps,
    }
