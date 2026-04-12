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
    assert "gobuster" in result.stdout
    assert "proxychains4" in result.stdout
    assert "socat" in result.stdout
    assert "rustscan" in result.stdout
    assert "cloudfox" in result.stdout
    assert "fscan" in result.stdout
    assert "stowaway" in result.stdout
    assert "linpeas" in result.stdout
    assert "pspy" in result.stdout
    assert "metasploit-framework" in result.stdout
