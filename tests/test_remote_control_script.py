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
    assert "debug-update" in result.stdout
    assert "competition-start" in result.stdout
    assert "competition-restart" in result.stdout
    assert "competition-stop" in result.stdout
    assert "competition-status" in result.stdout
    assert "ui-start" in result.stdout
    assert "ui-restart" in result.stdout
    assert "ui-stop" in result.stdout
    assert "ui-status" in result.stdout


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


def test_remote_control_debug_does_not_require_update_on_dirty_tree() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        scripts_dir = root / "scripts"
        venv_bin = root / ".venv" / "bin"
        scripts_dir.mkdir(parents=True)
        venv_bin.mkdir(parents=True)

        (root / ".env").write_text("NIUNIU_AGENT_MODE=debug\n", encoding="utf-8")
        (root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        (scripts_dir / "remote_control.sh").write_text(
            SCRIPT_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        fake_agent = venv_bin / "niuniu-agent"
        fake_agent.write_text(
            "#!/usr/bin/env bash\n"
            "echo \"agent:$*\"\n",
            encoding="utf-8",
        )
        fake_agent.chmod(0o755)

        result = subprocess.run(
            ["bash", str(scripts_dir / "remote_control.sh"), "debug"],
            cwd=root,
            env={"REMOTE_CONTROL_USE_UV": "0"},
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "agent:run --mode debug" in result.stdout


def test_remote_control_prefers_uv_sync_and_uv_run() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "uv sync" in script
    assert "uv run niuniu-agent run --mode competition" in script
    assert "uv run niuniu-agent run --mode debug" in script


def test_remote_control_competition_start_persists_run_id_file_and_stop_removes_it() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        scripts_dir = root / "scripts"
        scripts_dir.mkdir(parents=True)
        fake_bin = root / "fake-bin"
        fake_bin.mkdir(parents=True)

        (root / ".env").write_text("NIUNIU_AGENT_MODE=competition\n", encoding="utf-8")
        (scripts_dir / "remote_control.sh").write_text(
            SCRIPT_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        fake_uv = fake_bin / "uv"
        fake_uv.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = \"run\" ]; then\n"
            "  shift\n"
            "  sleep 60\n"
            "else\n"
            "  exit 0\n"
            "fi\n",
            encoding="utf-8",
        )
        fake_uv.chmod(0o755)

        start = subprocess.run(
            ["bash", str(scripts_dir / "remote_control.sh"), "competition-start"],
            cwd=root,
            env={
                "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                "REMOTE_CONTROL_USE_UV": "1",
                "HOME": str(root),
            },
            capture_output=True,
            text=True,
            check=False,
        )

        run_id_file = root / "runtime" / "competition.run_id"
        pid_file = root / "runtime" / "competition.pid"

        assert start.returncode == 0
        assert run_id_file.exists()
        assert run_id_file.read_text(encoding="utf-8").strip()
        assert pid_file.exists()

        stop = subprocess.run(
            ["bash", str(scripts_dir / "remote_control.sh"), "competition-stop"],
            cwd=root,
            env={
                "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                "REMOTE_CONTROL_USE_UV": "1",
                "HOME": str(root),
            },
            capture_output=True,
            text=True,
            check=False,
        )

        assert stop.returncode == 0
        assert not run_id_file.exists()
