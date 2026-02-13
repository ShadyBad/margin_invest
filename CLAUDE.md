# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Management

Use **uv** for all Python project and package management:

```bash
uv add <package>          # Add a dependency
uv remove <package>       # Remove a dependency
uv sync                   # Sync dependencies from pyproject.toml
uv run <command>          # Run a command in the virtual environment
uv lock                   # Update the lockfile
```

## Running the Application

```bash
uv run python main.py     # Run the main application
```

## Python Version

This project requires Python 3.13.5+ (specified in `.python-version`).
