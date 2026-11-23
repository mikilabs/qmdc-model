"""Source-location and failure-class diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model.cli import main  # noqa: E402
from qmdc_model.linter import lint_workspace  # noqa: E402

CASES = Path(__file__).parent / "lint"


def test_issue_location_comes_from_qmdc():
    issue = lint_workspace(CASES / "006-enum-violation",
                           enforce_workspace_contract=False)[0]
    assert issue.file == "readme.qmd.md"
    assert issue.line == 14


def test_human_output_prints_source_location(capsys):
    assert main(["lint", str(CASES / "006-enum-violation")]) == 1
    out = capsys.readouterr().out
    assert "[enum_violation] readme.qmd.md:14" in out


def test_evaluation_failure_is_not_reported_as_bad_domain_data(capsys):
    issues = lint_workspace(CASES / "032-rule-eval-failed",
                            enforce_workspace_contract=False)
    assert [i.code for i in issues] == ["rule_eval_failed"]
    assert "TypeError" in issues[0].message
    assert "rule says: session s1 has no incoming references" in issues[0].message

    assert main(["lint", str(CASES / "032-rule-eval-failed")]) == 1
    out = capsys.readouterr().out
    assert "[rule_eval_failed]" in out
    assert "readme.qmd.md:8" in out
