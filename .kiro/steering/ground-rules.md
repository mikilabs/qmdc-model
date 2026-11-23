# Tech Stack

- Language: Python 3.12
- Package manager: uv (inferred from pyproject.toml layout and .python-version)
- Build config: pyproject.toml (PEP 621)

NEVER execute mutating git commands! Ask the user to do them manually.

## QMD
This repo uses .qmd.md files for documentation, prefer qmdc mcp first before reading or editing them!

## Common Commands

```bash
# Run the app
uv run hello.py

# Add a dependency
uv add <package>

# Sync/install dependencies
uv sync

# Run tests (when added)
uv run pytest
```

## Conventions

- Use `uv` for all dependency and environment management — do not use pip or virtualenv directly.
- Python version is pinned to 3.12 via `.python-version`.

## Shell Commands

NEVER do long multiline terminal commands, you are hanging the terminal with them!

Always use throwaway scripts in the local .tmp folder 