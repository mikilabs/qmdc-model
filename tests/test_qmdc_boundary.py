"""qmdc is the sole parser; failures at that boundary must never become a clean lint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import qmdc_model.linter as linter  # noqa: E402


def test_invalid_validate_json_fails_closed(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setattr(
        linter, "run_qmdc",
        lambda args: subprocess.CompletedProcess(args, 0, "not-json", ""),
    )
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["qmdc_failed"]
    assert "invalid JSON" in issues[0].message


def test_query_failure_is_structured_not_a_traceback(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()

    def fake(args):
        if args[:2] == ["workspace", "validate"]:
            return subprocess.CompletedProcess(args, 0, "[]", "")
        return subprocess.CompletedProcess(args, 7, "", "index unavailable")

    monkeypatch.setattr(linter, "run_qmdc", fake)
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["qmdc_failed"]
    assert "index unavailable" in issues[0].message


def test_non_numeric_diagnostic_line_is_qmdc_failed(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    payload = '[{"type":"broken_link","message":"x","line":"not-a-number"}]'
    monkeypatch.setattr(
        linter, "run_qmdc",
        lambda args: subprocess.CompletedProcess(args, 1, payload, ""),
    )
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["qmdc_failed"]
    assert "invalid line" in issues[0].message


def test_missing_qmdc_binary_is_structured_not_traceback(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()

    def missing(*args, **kwargs):
        raise FileNotFoundError("qmdc not found")

    monkeypatch.setattr(subprocess, "run", missing)
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["qmdc_failed"]
    assert "could not execute qmdc" in issues[0].message


@pytest.mark.parametrize(
    "query_payload",
    [
        "7",
        '{"columns":["__id"],"rows":[42]}',
        '{"columns":["__id","data"],"rows":[["x","[]"]]}',
    ],
)
def test_malformed_query_shapes_are_qmdc_failed(tmp_path: Path, monkeypatch, query_payload: str):
    ws = tmp_path / "ws"
    ws.mkdir()

    def fake(args):
        if args[:2] == ["workspace", "validate"]:
            return subprocess.CompletedProcess(args, 0, "[]", "")
        return subprocess.CompletedProcess(args, 0, query_payload, "")

    monkeypatch.setattr(linter, "run_qmdc", fake)
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["qmdc_failed"]


def test_nonzero_validate_with_empty_array_fails_closed(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setattr(
        linter, "run_qmdc",
        lambda args: subprocess.CompletedProcess(args, 3, "[]", "fatal: index corrupt"),
    )
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["qmdc_failed"]
    assert "exit 3" in issues[0].message


def test_discovered_file_omitted_from_object_index_fails_closed(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()

    objects = {
        "columns": ["__global_id", "__id", "__kind", "__file", "__line", "data"],
        "rows": [["::w", "w", "__Workspace", "readme.qmd.md", 1, "{}"]],
    }
    edges = {"columns": ["source_id", "target_id", "source_field", "edge_type"], "rows": []}

    def fake(args):
        if args[:2] == ["workspace", "validate"]:
            return subprocess.CompletedProcess(args, 0, "[]", "")
        if args[:2] == ["workspace", "parse"]:
            return subprocess.CompletedProcess(
                args, 0, '{"files":["readme.qmd.md","roster.qmd.md"],"objects":[]}', "")
        payload = objects if "FROM objects" in args[2] else edges
        import json
        return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")

    monkeypatch.setattr(linter, "run_qmdc", fake)
    issues = linter.lint_workspace(ws)
    assert [i.code for i in issues] == ["source_unparsed"]
    assert issues[0].file == "roster.qmd.md"


def test_bundled_qmdc_wins_over_path(monkeypatch):
    """The qmdc installed with this package is used even when PATH has none."""
    monkeypatch.setenv("PATH", "")
    exe = Path(linter.qmdc_executable())
    assert Path(sys.prefix) in exe.parents
    out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, check=True)
    assert out.stdout.startswith("qmdc ")
