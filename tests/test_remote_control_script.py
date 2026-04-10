from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "remote_control.sh"


def test_remote_control_script_help_lists_commands() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "update" in result.stdout
    assert "debug" in result.stdout
    assert "competition-start" in result.stdout
    assert "competition-stop" in result.stdout
    assert "competition-status" in result.stdout


def test_remote_control_script_rejects_unknown_command() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "unknown-command"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Unknown command" in result.stderr
