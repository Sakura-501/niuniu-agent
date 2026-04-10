from __future__ import annotations

import subprocess
from pathlib import Path
import tempfile


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


def test_remote_control_update_cleans_bootstrap_script_dir() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        origin = root / "origin.git"
        seed = root / "seed"
        target = root / "target"

        subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "init", str(seed)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(seed), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(seed), "config", "user.email", "test@example.com"], check=True)
        (seed / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(seed), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(seed), "commit", "-m", "init"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(seed), "branch", "-M", "main"], check=True)
        subprocess.run(["git", "-C", str(seed), "remote", "add", "origin", str(origin)], check=True)
        subprocess.run(["git", "-C", str(seed), "push", "origin", "main"], check=True, capture_output=True, text=True)

        subprocess.run(["git", "clone", str(origin), str(target)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(target), "checkout", "main"], check=True, capture_output=True, text=True)

        scripts_dir = target / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "remote_control.sh").write_text(
            SCRIPT_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        result = subprocess.run(
            ["bash", str(scripts_dir / "remote_control.sh"), "update"],
            cwd=target,
            env={
                **dict(),
                "PATH": str(Path("/usr/bin")) + ":" + str(Path("/bin")) + ":" + str(Path("/usr/sbin")) + ":" + str(Path("/sbin")),
                "REMOTE_CONTROL_SKIP_INSTALL": "1",
            },
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        status = subprocess.run(
            ["git", "-C", str(target), "status", "--short"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert status.stdout.strip() == ""
