"""
Tests for ``qmdc-model upgrade``.

The contract under test: the tool OWNS ``*.vendor.qmd.md``. Upgrade creates a missing
one, rewrites a stale one, deletes one this version no longer ships, keeps exactly one
copy across all ``_metamodel`` namespaces, and touches nothing else — the workspace's
readmes, KindSchemas and LintRules belong to the author.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model import __version__  # noqa: E402
from qmdc_model.cli import MARKER_OPEN, _shipped_vendor, _strip_marker, main  # noqa: E402

VENDORED = "_metamodel/metaschema.vendor.qmd.md"


def _init(tmp_path: Path, name: str = "ws") -> Path:
    ws = tmp_path / name
    assert main(["init", str(ws)]) == 0
    return ws


def test_init_stamps_the_vendored_file_with_the_tool_version(tmp_path: Path):
    ws = _init(tmp_path)
    text = (ws / VENDORED).read_text(encoding="utf-8")

    assert text.startswith(f"{MARKER_OPEN}{__version__} ")
    assert "Do not edit by hand" in text.partition("-->")[0]
    assert _strip_marker(text) == _shipped_vendor()["metaschema.vendor.qmd.md"]


def test_upgrade_is_a_no_op_on_a_fresh_workspace(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    before = (ws / VENDORED).read_text(encoding="utf-8")
    capsys.readouterr()

    assert main(["upgrade", str(ws)]) == 0
    assert f"already at {__version__}" in capsys.readouterr().out
    assert (ws / VENDORED).read_text(encoding="utf-8") == before


def test_upgrade_rewrites_a_stale_vendored_file(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    (ws / VENDORED).write_text("# stale, from an older version\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["upgrade", str(ws)]) == 0
    assert "updated" in capsys.readouterr().out
    text = (ws / VENDORED).read_text(encoding="utf-8")
    assert _strip_marker(text) == _shipped_vendor()["metaschema.vendor.qmd.md"]
    assert text.startswith(f"{MARKER_OPEN}{__version__} ")


def test_upgrade_recreates_a_deleted_vendored_file(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    (ws / VENDORED).unlink()
    capsys.readouterr()

    assert main(["upgrade", str(ws)]) == 0
    assert "created" in capsys.readouterr().out
    assert (ws / VENDORED).is_file()


def test_upgrade_deletes_a_vendored_file_this_version_does_not_ship(tmp_path: Path, capsys):
    """Full ownership includes removal — a vendored file dropped upstream must not linger."""
    ws = _init(tmp_path)
    stray = ws / "_metamodel" / "legacy-kinds.vendor.qmd.md"
    stray.write_text("# shipped by an older version\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["upgrade", str(ws)]) == 0
    assert "deleted" in capsys.readouterr().out
    assert not stray.exists()


def test_upgrade_keeps_one_copy_per_workspace(tmp_path: Path, capsys):
    """Two vendored copies duplicate fixed object ids, which makes every reference in them
    ambiguous — so upgrade updates one and removes the rest."""
    ws = _init(tmp_path)
    nested = ws / "billing" / "_metamodel"
    nested.mkdir(parents=True)
    dup = nested / "metaschema.vendor.qmd.md"
    dup.write_text("# stale second copy\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["upgrade", str(ws)]) == 0
    assert "duplicate copy" in capsys.readouterr().out
    assert not dup.exists()
    shipped = _shipped_vendor()["metaschema.vendor.qmd.md"]
    assert _strip_marker((ws / VENDORED).read_text(encoding="utf-8")) == shipped


def test_upgrade_updates_a_copy_that_lives_in_a_nested_namespace(tmp_path: Path):
    """The one copy need not sit in the root namespace; upgrade must not add a second."""
    ws = _init(tmp_path)
    (ws / VENDORED).unlink()
    nested = ws / "billing" / "_metamodel"
    nested.mkdir(parents=True)
    (nested / "metaschema.vendor.qmd.md").write_text("# stale\n", encoding="utf-8")

    assert main(["upgrade", str(ws)]) == 0
    assert not (ws / VENDORED).exists()
    shipped = _shipped_vendor()["metaschema.vendor.qmd.md"]
    assert _strip_marker((nested / "metaschema.vendor.qmd.md").read_text(encoding="utf-8")) == shipped


def test_upgrade_leaves_author_owned_files_alone(tmp_path: Path):
    ws = _init(tmp_path)
    mine = {
        ws / "readme.qmd.md": "# Mine [[mine: __Workspace]]\n",
        ws / "_metamodel" / "readme.qmd.md": "# Meta [[_metamodel: __Namespace]]\n",
        ws / "_metamodel" / "my-kinds.qmd.md": "# Kinds [[k: __Namespace]]\n",
    }
    for path, text in mine.items():
        path.write_text(text, encoding="utf-8")
    (ws / VENDORED).write_text("# stale\n", encoding="utf-8")

    assert main(["upgrade", str(ws)]) == 0
    for path, text in mine.items():
        assert path.read_text(encoding="utf-8") == text, path


def test_dry_run_reports_the_plan_and_writes_nothing(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    (ws / VENDORED).write_text("# stale\n", encoding="utf-8")
    stray = ws / "_metamodel" / "gone.vendor.qmd.md"
    stray.write_text("# dropped upstream\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["upgrade", str(ws), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "would update" in out and "would delete" in out
    assert "nothing written" in out
    assert (ws / VENDORED).read_text(encoding="utf-8") == "# stale\n"
    assert stray.is_file()


def test_upgrade_without_a_metamodel_says_so(tmp_path: Path, capsys):
    bare = tmp_path / "bare"
    bare.mkdir()

    assert main(["upgrade", str(bare)]) == 0
    assert "run 'qmdc-model init' first" in capsys.readouterr().out


def test_upgrade_refuses_a_non_directory(tmp_path: Path, capsys):
    target = tmp_path / "file.md"
    target.write_text("x", encoding="utf-8")

    assert main(["upgrade", str(target)]) == 2
    assert "not a directory" in capsys.readouterr().out


def test_upgraded_workspace_lints_clean(tmp_path: Path):
    """The point of the one-copy rule: duplicate vendored ids would raise
    ambiguous_reference on every reference inside the metaschema."""
    from qmdc_model.linter import lint_workspace

    ws = _init(tmp_path)
    nested = ws / "billing" / "_metamodel"
    nested.mkdir(parents=True)
    (nested / "metaschema.vendor.qmd.md").write_text("# stale second copy\n", encoding="utf-8")
    # ids are workspace-unique, so a per-namespace metamodel carries its own id
    (nested / "readme.qmd.md").write_text("# Metamodel [[billing_metamodel: __Namespace]]\n",
                                          encoding="utf-8")

    assert main(["upgrade", str(ws)]) == 0
    assert lint_workspace(ws) == []


def test_upgrade_refuses_symlinked_metamodel_directory(tmp_path: Path, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    doomed = victim / "legacy.vendor.qmd.md"
    doomed.write_text("do not delete\n", encoding="utf-8")
    (ws / "_metamodel").symlink_to(victim, target_is_directory=True)

    assert main(["upgrade", str(ws), "--dry-run"]) == 2
    out = capsys.readouterr().out
    assert "refusing symlink inside workspace" in out
    assert str(victim) in out  # no misleading workspace-relative safety plan
    assert doomed.read_text(encoding="utf-8") == "do not delete\n"

    assert main(["upgrade", str(ws)]) == 2
    assert doomed.read_text(encoding="utf-8") == "do not delete\n"


def test_upgrade_refuses_symlinked_vendor_file(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    vendor.unlink()
    victim = tmp_path / "outside.vendor.qmd.md"
    victim.write_text("do not overwrite\n", encoding="utf-8")
    vendor.symlink_to(victim)
    capsys.readouterr()

    assert main(["upgrade", str(ws)]) == 2
    out = capsys.readouterr().out
    assert "refusing symlink inside workspace" in out
    assert str(victim) in out
    assert victim.read_text(encoding="utf-8") == "do not overwrite\n"


def test_upgrade_reports_vendor_directory_without_traceback(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    vendor.unlink()
    vendor.mkdir()
    capsys.readouterr()

    assert main(["upgrade", str(ws), "--dry-run"]) == 2
    assert "vendor path is not a regular file" in capsys.readouterr().out


def test_upgrade_preflights_read_only_vendor(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    vendor.write_text("# stale\n", encoding="utf-8")
    vendor.chmod(0o444)
    capsys.readouterr()
    try:
        assert main(["upgrade", str(ws)]) == 2
        assert "vendor file is not writable" in capsys.readouterr().out
        assert vendor.read_text(encoding="utf-8") == "# stale\n"
    finally:
        vendor.chmod(0o644)


def test_init_refuses_symlinked_metamodel_directory(tmp_path: Path, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    (ws / "_metamodel").symlink_to(victim, target_is_directory=True)

    assert main(["init", str(ws)]) == 2
    assert "refusing symlink inside workspace" in capsys.readouterr().out
    assert list(victim.iterdir()) == []


def test_upgrade_replaces_local_hardlink_without_mutating_outside_name(tmp_path: Path):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    vendor.unlink()
    victim = tmp_path / "outside.vendor.qmd.md"
    victim.write_text("outside must stay stale\n", encoding="utf-8")
    os.link(victim, vendor)

    assert main(["upgrade", str(ws)]) == 0
    assert victim.read_text(encoding="utf-8") == "outside must stay stale\n"
    assert _strip_marker(vendor.read_text(encoding="utf-8")) == (
        _shipped_vendor()["metaschema.vendor.qmd.md"]
    )
    assert os.stat(victim).st_ino != os.stat(vendor).st_ino


def test_dry_run_reports_plan_even_when_vendor_is_read_only(tmp_path: Path, capsys):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    vendor.write_text("# stale\n", encoding="utf-8")
    vendor.chmod(0o444)
    capsys.readouterr()
    try:
        assert main(["upgrade", str(ws), "--dry-run"]) == 0
        assert "would update" in capsys.readouterr().out
        assert vendor.read_text(encoding="utf-8") == "# stale\n"
    finally:
        vendor.chmod(0o644)


def test_upgrade_preserves_existing_file_mode(tmp_path: Path):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    vendor.write_text("# stale\n", encoding="utf-8")
    vendor.chmod(0o664)

    assert main(["upgrade", str(ws)]) == 0
    assert stat.S_IMODE(vendor.stat().st_mode) == 0o664


def test_upgrade_repairs_marker_drift_even_when_body_matches(tmp_path: Path):
    ws = _init(tmp_path)
    vendor = ws / VENDORED
    body = _shipped_vendor()["metaschema.vendor.qmd.md"]
    vendor.write_text("<!-- qmdc-model 0.0.0 — ancient -->\n\n" + body, encoding="utf-8")

    assert main(["upgrade", str(ws)]) == 0
    assert vendor.read_text(encoding="utf-8") == (
        f"{MARKER_OPEN}{__version__} — generated file owned by the tool: "
        "`qmdc-model upgrade` rewrites or deletes it. Do not edit by hand. -->\n\n" + body
    )
