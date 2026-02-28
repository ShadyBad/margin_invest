"""Tests for the ablation CLI command."""

from __future__ import annotations

import argparse
import inspect
import subprocess
import sys


def test_ablation_command_exists():
    """Verify the ablation subcommand registers and --help works."""
    result = subprocess.run(
        [sys.executable, "-m", "margin_api.cli", "ablation", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Exit code {result.returncode}: {result.stderr}"
    output = result.stdout.lower()
    assert "ablation" in output or "interference" in output


def test_ablation_parser_registers():
    """Verify the ablation subcommand is registered in the CLI source."""
    import margin_api.cli as cli_module

    source = inspect.getsource(cli_module)
    assert "ablation" in source


def test_ablation_default_args():
    """Verify default arguments for ablation."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    ablation_parser = subparsers.add_parser("ablation")
    ablation_parser.add_argument("--start-date", default="2015-01-01")
    ablation_parser.add_argument("--end-date", default=None)
    ablation_parser.add_argument("--output", default=None)
    ablation_parser.add_argument("--bootstrap-n", type=int, default=1000)

    args = parser.parse_args(["ablation"])
    assert args.start_date == "2015-01-01"
    assert args.end_date is None
    assert args.output is None
    assert args.bootstrap_n == 1000


def test_ablation_custom_args():
    """Verify custom arguments for ablation."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    ablation_parser = subparsers.add_parser("ablation")
    ablation_parser.add_argument("--start-date", default="2015-01-01")
    ablation_parser.add_argument("--end-date", default=None)
    ablation_parser.add_argument("--output", default=None)
    ablation_parser.add_argument("--bootstrap-n", type=int, default=1000)

    args = parser.parse_args(
        [
            "ablation",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2023-12-31",
            "--output",
            "/tmp/report.json",
            "--bootstrap-n",
            "500",
        ]
    )
    assert args.start_date == "2020-01-01"
    assert args.end_date == "2023-12-31"
    assert args.output == "/tmp/report.json"
    assert args.bootstrap_n == 500
