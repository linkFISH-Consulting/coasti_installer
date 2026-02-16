import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from coasti import cli


@pytest.mark.parametrize(
    "data",
    [
        '{"vcs_repo_type" : "skip"}',
        '{"vcs_repo_type" : "local"}',
        '{"vcs_repo_type" : "remote", "vcs_online_repo" : "gh.dummy"}',
    ],
)
def test_init_success(cli_runner: CliRunner, tmp_path: Path, data: str):
    """Test successful `coasti init` command.

    You need to run create_template_bundle.py before this can succeed.
    """
    coasti_dir = tmp_path / "coasti"

    command = ["init", "--data", data]
    command += ["--vcs-ref", "HEAD"]  # so we always use the current branch when local
    command += [str(coasti_dir)]

    result = cli_runner.invoke(cli.app, command)

    assert result.exit_code == 0
    assert coasti_dir.is_dir()

    assert (coasti_dir / "config" / "install_answers.yml").exists()

    with (coasti_dir / "config" / "install_answers.yml").open() as f:
        loaded_yaml = yaml.safe_load(f)

    copier_data = json.loads(data)

    # Validate expected content
    assert loaded_yaml is not None
    assert "vcs_repo_type" in loaded_yaml
    assert loaded_yaml["vcs_repo_type"] == copier_data["vcs_repo_type"]

    if copier_data["vcs_repo_type"] == "remote":
        assert "vcs_online_repo" in loaded_yaml
        assert loaded_yaml["vcs_online_repo"] == "gh.dummy"
