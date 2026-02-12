"""Pytest configuration and fixtures for coasti tests."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Return a Typer CliRunner for testing CLI commands."""
    return CliRunner()
