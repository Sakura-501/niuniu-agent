from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_toolchain.sh"


def test_install_toolchain_script_prints_expected_commands() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "print"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ripgrep" in result.stdout
    assert "openssl" in result.stdout
    assert "impacket" in result.stdout
    assert "masscan" in result.stdout
    assert "kerbrute" in result.stdout
