from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocalExpEntry:
    challenge_code: str
    product: str
    references: tuple[str, ...]


LOCAL_EXP_ENTRIES: tuple[LocalExpEntry, ...] = (
    LocalExpEntry(
        challenge_code="BpOxyTLXpdveWilhjRCFjZtMGjgr",
        product="Dify / Next.js",
        references=(
            "/root/niuniu-agent/exp/CVE-2025-55182/README.md",
            "/root/niuniu-agent/exp/CVE-2025-55182/poc.py",
            "/root/niuniu-agent/exp/CVE-2025-29927-POC/README.md",
        ),
    ),
    LocalExpEntry(
        challenge_code="3ZsOMt8EHQa9bvynN7WTlSJZDOGzL8t",
        product="GeoServer / GeoTools",
        references=(
            "/root/niuniu-agent/exp/CVE-2024-36401/README.md",
        ),
    ),
    LocalExpEntry(
        challenge_code="3ZdueytTkJeRy2wiYmJiqwrzP2XiNqs",
        product="Gradio",
        references=(
            "/root/niuniu-agent/exp/CVE-2024-51751/Gradio vulnerable to arbitrary file read with File and UploadButton components.md",
        ),
    ),
    LocalExpEntry(
        challenge_code="P6MIR6VZretJ88R6OMnGVs3itvbkjCmv0y3mPHGU",
        product="Terminal access daemon",
        references=(
            "/root/niuniu-agent/exp/CVE-2026-24061/readme.md",
        ),
    ),
)


def has_local_exp_support(challenge_code: str) -> bool:
    return any(entry.challenge_code == challenge_code for entry in LOCAL_EXP_ENTRIES)


def get_local_exp_entry(challenge_code: str) -> LocalExpEntry | None:
    return next((entry for entry in LOCAL_EXP_ENTRIES if entry.challenge_code == challenge_code), None)
