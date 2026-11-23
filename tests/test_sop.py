"""
Tests for ``qmdc-model sop``.

The SOP ships inside the package so an agent working in any repository can obtain the
procedure that matches the installed checks — no per-project copy to go stale. These
tests pin that contract: the text comes out whole, ``--path`` points at the same bytes,
and every ``qmdc-model <subcommand>`` the SOP tells a reader to run actually exists.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model.cli import main  # noqa: E402

TITLE = "# SOP: Creating an Emerging Metamodel for a QMD Workspace"


def test_sop_prints_the_whole_document(capsys):
    assert main(["sop"]) == 0
    out = capsys.readouterr().out

    assert out.startswith(TITLE)
    for section in ("## Prerequisites", "## Step 1: Identify Anchor Entities",
                    "## Step 7: Evolve the Metamodel", "## Quick Reference"):
        assert section in out, section
    assert len(out.splitlines()) > 400  # the full procedure, not a summary


def test_sop_path_points_at_the_same_bytes(capsys):
    assert main(["sop", "--path"]) == 0
    path = Path(capsys.readouterr().out.strip())
    assert path.is_file()
    assert path.name == "sop-metamodel-creation.md"

    assert main(["sop"]) == 0
    assert capsys.readouterr().out == path.read_text(encoding="utf-8")


def test_sop_only_names_commands_that_exist(capsys):
    """Drift guard: a renamed or dropped subcommand must not survive in the procedure."""
    assert main(["sop"]) == 0
    sop = capsys.readouterr().out

    named = set(re.findall(r"qmdc-model ([a-z][a-z0-9-]*)", sop))
    assert named, "the SOP should tell the reader which commands to run"

    implemented = set()
    for candidate in sorted(named):
        try:
            main([candidate, "--help"])
        except SystemExit as exit_code:  # argparse exits 0 on --help, 2 on unknown command
            if exit_code.code == 0:
                implemented.add(candidate)
        capsys.readouterr()

    assert named == implemented, f"SOP names commands the CLI does not have: {named - implemented}"
