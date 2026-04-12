from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "fetch_portable_tools.py"


def test_fetch_portable_tools_script_print_lists_expected_tools() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "print", "rustscan", "cloudfox", "frp", "fscan", "stowaway", "linpeas", "mimikatz"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "rustscan" in result.stdout
    assert "cloudfox" in result.stdout
    assert "frp" in result.stdout
    assert "fscan" in result.stdout
    assert "stowaway" in result.stdout
    assert "linpeas" in result.stdout
    assert "mimikatz" in result.stdout
