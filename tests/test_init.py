"""
Tests for ``qmdc-model init``.

Covers what the command guarantees: it creates the workspace directory (with parents),
writes a workspace-root ``readme.qmd.md`` declaring a ``__Workspace`` whose id is derived
from the directory name, vendors the metamodel, never overwrites an existing file, and
leaves a workspace that lints clean.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model.cli import _workspace_id, _workspace_label, main  # noqa: E402
from qmdc_model.linter import lint_workspace  # noqa: E402

SCAFFOLD = (
    "readme.qmd.md",
    "_metamodel/readme.qmd.md",
    "_metamodel/metaschema.vendor.qmd.md",
)


def test_init_creates_missing_directory(tmp_path: Path):
    """The target directory need not exist — parents are created too."""
    ws = tmp_path / "nested" / "my-workspace"
    assert main(["init", str(ws)]) == 0
    assert ws.is_dir()
    for rel in SCAFFOLD:
        assert (ws / rel).is_file(), rel


def test_root_readme_declares_workspace_object(tmp_path: Path):
    ws = tmp_path / "my-workspace"
    assert main(["init", str(ws)]) == 0

    root = (ws / "readme.qmd.md").read_text(encoding="utf-8")
    assert "[[my_workspace: __Workspace]]" in root
    assert root.startswith("# my-workspace ")  # label keeps the directory name verbatim
    assert "{{" not in root  # every placeholder substituted


@pytest.mark.parametrize(
    "dirname,expected",
    [
        ("my-workspace", "my_workspace"),
        ("QMDC Model", "qmdc_model"),
        ("weird..name--1", "weird_name_1"),
        ("2026-notes", "ws_2026_notes"),
        ("мойпроект", "мойпроект"),
        ("___", "ws_bda25155"),
    ],
)
def test_workspace_id_derivation(dirname: str, expected: str):
    assert _workspace_id(dirname) == expected


def test_init_never_overwrites_existing_files(tmp_path: Path, capsys):
    """Re-running init on an edited workspace is safe: it reports skips, changes nothing."""
    ws = tmp_path / "ws"
    main(["init", str(ws)])
    mine = "# Mine [[mine: __Workspace]]\n"
    (ws / "readme.qmd.md").write_text(mine, encoding="utf-8")
    capsys.readouterr()

    assert main(["init", str(ws)]) == 0
    assert capsys.readouterr().out.count("skipped") == len(SCAFFOLD)
    assert (ws / "readme.qmd.md").read_text(encoding="utf-8") == mine


def test_init_refuses_a_file_target(tmp_path: Path, capsys):
    target = tmp_path / "not-a-dir"
    target.write_text("x", encoding="utf-8")

    assert main(["init", str(target)]) == 2
    assert "not a directory" in capsys.readouterr().out


def test_fresh_workspace_lints_clean(tmp_path: Path):
    """A just-initialized workspace must pass the linter with no issues."""
    ws = tmp_path / "fresh-ws"
    assert main(["init", str(ws)]) == 0
    assert lint_workspace(ws) == []


@pytest.mark.parametrize(
    "dirname",
    [
        "evil[[pwned: Fake]]ws",
        "{{id}}",
        "two\nlines",
        "🚀",
    ],
)
def test_adversarial_directory_name_still_makes_exactly_one_workspace(tmp_path: Path, dirname: str):
    """A directory name is data, never QMD syntax: init must neither inject nor re-parent."""
    ws = tmp_path / dirname
    assert main(["init", str(ws)]) == 0
    assert lint_workspace(ws) == []

    # Ask qmdc — not our code — what the generated file means.
    import json
    import subprocess
    from qmdc_model.linter import qmdc_executable
    parsed = subprocess.run(
        [qmdc_executable(), "workspace", "parse", str(ws), "--format", "full"],
        capture_output=True, text=True, check=True,
    )
    objects = json.loads(parsed.stdout)["objects"]
    workspaces = [o for o in objects if o.get("__kind") == "__Workspace"]
    assert len(workspaces) == 1
    assert all(o.get("__kind") != "Fake" for o in objects)


def test_workspace_label_neutralizes_qmd_syntax_and_line_breaks():
    assert _workspace_label("evil[[pwned: Fake]]ws") == "evil［［pwned: Fake］］ws"
    assert _workspace_label("two\nlines") == "two lines"


@pytest.mark.parametrize("command", ["init", "upgrade", "lint"])
def test_explicit_empty_workspace_path_is_rejected(command: str, capsys):
    assert main([command, ""]) == 2
    assert "workspace path must not be empty" in capsys.readouterr().out
