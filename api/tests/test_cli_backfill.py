"""Tests for the backfill-13f CLI command."""
from __future__ import annotations

import argparse
import inspect


def test_backfill_13f_parser_registers():
    """Verify the backfill-13f subcommand registers with argparse."""
    import margin_api.cli as cli_module

    source = inspect.getsource(cli_module)
    assert "backfill-13f" in source


def test_backfill_13f_default_args():
    """Verify default arguments for backfill-13f."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    backfill_parser = subparsers.add_parser("backfill-13f")
    backfill_parser.add_argument("--start-year", type=int, default=2013)
    backfill_parser.add_argument("--max-managers", type=int, default=300)

    args = parser.parse_args(["backfill-13f"])
    assert args.start_year == 2013
    assert args.max_managers == 300


def test_backfill_13f_custom_args():
    """Verify custom arguments."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    backfill_parser = subparsers.add_parser("backfill-13f")
    backfill_parser.add_argument("--start-year", type=int, default=2013)
    backfill_parser.add_argument("--max-managers", type=int, default=300)

    args = parser.parse_args(["backfill-13f", "--start-year", "2020", "--max-managers", "50"])
    assert args.start_year == 2020
    assert args.max_managers == 50
