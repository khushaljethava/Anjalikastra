from typer.testing import CliRunner

from anjalikastra.cli import app

runner = CliRunner()


def test_dry_run_prints_plan_and_exits_zero():
    result = runner.invoke(app, ["https://example.com", "--dry-run"])
    assert result.exit_code == 0
    assert "plan for https://example.com" in result.output
    assert "Discovery" in result.output


def test_rejects_url_without_scheme():
    result = runner.invoke(app, ["example.com", "--dry-run"])
    assert result.exit_code == 2
