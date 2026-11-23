"""qmdc-model — metamodel operator and linter for QMD workspaces."""

from importlib.metadata import version

# Single source of truth is pyproject.toml; scripts/bump_version.py changes it.
__version__ = version("qmdc-model")
