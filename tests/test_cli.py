from typer.testing import CliRunner

from niuniu_agent.cli import app


def test_cli_exposes_run_subcommand() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Commands" in result.stdout
    assert "run" in result.stdout

    run_result = runner.invoke(app, ["run", "--help"])

    assert run_result.exit_code == 0


def test_cli_help_mentions_debug_chat_behavior() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["run", "--help"])

    assert result.exit_code == 0
    assert "--mode" in result.stdout
