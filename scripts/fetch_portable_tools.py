#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools"
BIN_DIR = TOOLS_ROOT / "bin"
CACHE_DIR = TOOLS_ROOT / "portable"


@dataclass(frozen=True, slots=True)
class PortableTool:
    name: str
    repo: str
    assets: dict[str, tuple[str, ...]]
    binaries: tuple[str, ...]
    archive_only: bool = False


TOOLS: dict[str, PortableTool] = {
    "rustscan": PortableTool(
        name="rustscan",
        repo="bee-san/RustScan",
        assets={
            "darwin_arm64": ("aarch64-macos-rustscan.tar.gz.zip",),
            "linux_amd64": ("x86_64-linux-rustscan.tar.gz.zip",),
        },
        binaries=("rustscan",),
    ),
    "cloudfox": PortableTool(
        name="cloudfox",
        repo="BishopFox/cloudfox",
        assets={
            "darwin_arm64": ("cloudfox-macos-arm64.zip",),
            "linux_amd64": ("cloudfox-linux-amd64.zip",),
        },
        binaries=("cloudfox",),
    ),
    "frp": PortableTool(
        name="frp",
        repo="fatedier/frp",
        assets={
            "darwin_arm64": ("darwin_arm64.tar.gz",),
            "linux_amd64": ("linux_amd64.tar.gz",),
        },
        binaries=("frpc", "frps"),
    ),
    "stowaway": PortableTool(
        name="stowaway",
        repo="ph4ntonn/Stowaway",
        assets={
            "darwin_arm64": ("macos_arm64_admin", "macos_arm64_agent"),
            "linux_amd64": ("linux_x64_admin", "linux_x64_agent"),
        },
        binaries=("stowaway_admin", "stowaway_agent"),
    ),
    "fscan": PortableTool(
        name="fscan",
        repo="shadow1ng/fscan",
        assets={
            "darwin_arm64": ("fscan_mac_arm64",),
            "linux_amd64": ("fscan",),
        },
        binaries=("fscan",),
    ),
    "linpeas": PortableTool(
        name="linpeas",
        repo="peass-ng/PEASS-ng",
        assets={
            "darwin_arm64": ("linpeas_darwin_arm64",),
            "linux_amd64": ("linpeas_linux_amd64",),
        },
        binaries=("linpeas",),
    ),
    "pspy": PortableTool(
        name="pspy",
        repo="DominicBreuker/pspy",
        assets={
            "linux_amd64": ("pspy64",),
        },
        binaries=("pspy",),
    ),
    "mimikatz": PortableTool(
        name="mimikatz",
        repo="gentilkiwi/mimikatz",
        assets={
            "windows_x64_backup": ("mimikatz_trunk.zip",),
        },
        binaries=(),
        archive_only=True,
    ),
}


def current_target() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        system = "darwin"
    if system == "linux":
        system = "linux"
    if machine in {"x86_64", "amd64"}:
        machine = "amd64"
    elif machine in {"aarch64", "arm64"}:
        machine = "arm64"
    return f"{system}_{machine}"


def latest_release(repo: str) -> dict:
    with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/releases/latest") as response:
        return json.load(response)


def download(url: str, target: Path) -> None:
    with urllib.request.urlopen(url) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def install() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("print", "install"))
    parser.add_argument("tools", nargs="*", default=sorted(TOOLS))
    args = parser.parse_args()

    target = current_target()
    selected = [name for name in args.tools if name in TOOLS]

    if args.mode == "print":
        print(f"target={target}")
        for name in selected:
            tool = TOOLS[name]
            print(f"{tool.name}: repo={tool.repo} assets={tool.assets.get(target, ()) or tool.assets}")
        return 0

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    skipped: list[str] = []

    for name in selected:
        tool = TOOLS[name]
        asset_names = tool.assets.get(target)
        if asset_names is None:
            skipped.append(f"{name}:unsupported:{target}")
            continue

        release = latest_release(tool.repo)
        assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
        cache_dir = CACHE_DIR / name / target
        cache_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=cache_dir))
        try:
            extracted: list[Path] = []
            for asset_name in asset_names:
                url = assets.get(asset_name)
                if url is None:
                    matched_name = next(
                        (candidate for candidate in assets if candidate == asset_name or candidate.endswith(asset_name) or asset_name in candidate),
                        None,
                    )
                    url = assets.get(matched_name) if matched_name is not None else None
                if url is None:
                    raise RuntimeError(f"{name}: missing asset {asset_name} for {target}")
                archive_path = temp_dir / asset_name
                download(url, archive_path)
                if asset_name.endswith(".zip"):
                    with zipfile.ZipFile(archive_path) as zf:
                        zf.extractall(temp_dir)
                elif asset_name.endswith(".tar.gz"):
                    with tarfile.open(archive_path, "r:gz") as tf:
                        tf.extractall(temp_dir)
                else:
                    extracted.append(archive_path)

            if tool.archive_only:
                installed.append(f"{name}:archived")
                continue

            if tool.name == "stowaway":
                mapping = {
                    "admin": "stowaway_admin",
                    "agent": "stowaway_agent",
                }
                for source in extracted:
                    lowered = source.name.lower()
                    target_name = next((value for key, value in mapping.items() if key in lowered), source.name)
                    destination = BIN_DIR / target_name
                    shutil.copy2(source, destination)
                    destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    installed.append(target_name)
                continue

            for binary in tool.binaries:
                if tool.name == "frp":
                    source = next((path for path in temp_dir.rglob(binary) if path.is_file()), None)
                elif tool.name == "fscan":
                    source = next((path for path in extracted if path.name == asset_names[0]), None)
                elif tool.name == "linpeas":
                    source = next((path for path in extracted if path.name == asset_names[0]), None)
                elif tool.name == "cloudfox":
                    source = next((path for path in temp_dir.rglob("cloudfox") if path.is_file()), None)
                elif tool.name == "rustscan":
                    source = next((path for path in temp_dir.rglob("rustscan") if path.is_file()), None)
                elif tool.name == "pspy":
                    source = next((path for path in extracted if path.name == asset_names[0]), None)
                else:
                    source = next((path for path in temp_dir.rglob(binary) if path.is_file()), None)
                if source is None:
                    raise RuntimeError(f"{name}: failed to locate binary {binary}")
                destination = BIN_DIR / binary
                shutil.copy2(source, destination)
                destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                installed.append(binary)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    print(json.dumps({"target": target, "installed": installed, "skipped": skipped}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(install())
