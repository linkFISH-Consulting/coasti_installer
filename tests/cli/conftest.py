"""Pytest configuration and fixtures for coasti tests."""

import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Return a Typer CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def template_bundle():
    """
    Create needed bundle resources.

    We cannot include the bundle in git, because this would be circular, but still
    need to ship it - thus needed in tests.
    """
    from coasti import init
    from coasti.create_template_bundle import create_template_bundle

    repo_root = Path(__file__).resolve().parents[2]

    with tempfile.TemporaryDirectory() as tmpdir:
        # out_file persists until end of fixture (tempdir cleanup happens after yield)
        out_file = Path(tmpdir) / "template-repo.bundle"
        create_template_bundle(repo_root=repo_root, out_file=out_file)

        with mock.patch.object(
            init, "_get_template_bundle_path", return_value=out_file
        ):
            yield out_file

    return out_file
