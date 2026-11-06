"""Testes da interface inicial."""

import subprocess
import sys

from mindscreen import __version__


def test_package_has_version():
    assert __version__ == "0.1.0"


def test_cli_runs():
    result = subprocess.run(
        [sys.executable, "-m", "mindscreen"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "MindScreen AI" in result.stdout
    assert __version__ in result.stdout


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-m", "mindscreen", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == f"MindScreen AI {__version__}"
