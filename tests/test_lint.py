"""
Data-driven tests for the metamodel linter.

Tests are auto-discovered from case directories under ``tests/lint/`` that contain a
``readme.qmd.md`` (declaring a ``__Workspace``) and an ``_expected.json``. Adding a
test means adding data — no code changes here.

Add a new linter test by creating a directory with:
  - readme.qmd.md   (a __Workspace with the KindSchemas / LintRules / objects under test)
  - _expected.json  (the issues the linter must emit)
  - optionally more *.qmd.md files

Format of _expected.json:
{
  "issues": [
    {"severity": "error",   "code": "missing_required", "object": "w1", "field": "capacity"},
    {"severity": "warning", "code": "rule_failed",       "object": "ov1", "detail": "rule_overlay"},
    {"severity": "error",   "code": "duplicate_kind_schema",
     "global_id": "ws:a._metamodel:schema_issue", "field": "kind", "detail": "Issue"}
  ]
}

An empty ``"issues": []`` is the positive case (must lint clean). Comparison is by the
SET of ``(severity, code, <identity>, field, detail)`` tuples — order-independent, message
text is never compared. A missing or extra issue fails the case.

``<identity>`` is chosen PER EXPECTED ENTRY: an entry that declares ``global_id`` is matched
against the issue's qmdc global identity (``workspace:namespace:id``), any other entry
against its concise ``object`` id. Concise ids repeat across namespaces, so a case whose
point is WHICH namespace is blamed must pin ``global_id`` — with ``object`` alone such a
case passes no matter which of the equally-named candidates the linter names.
``--update`` keeps a case on global identity once any of its entries uses it.

Run one case with ``LINT_TEST_FILTER=006 uv run pytest tests/test_lint.py``.
Regenerate expected files (for manual review) with ``uv run python tests/test_lint.py --update``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model.linter import lint_workspace  # noqa: E402

LINT_TESTS_ROOT = Path(__file__).parent / "lint"


def find_lint_tests() -> list[tuple[str, Path, dict]]:
    """Discover linter test cases (dirs with readme.qmd.md + _expected.json)."""
    tests: list[tuple[str, Path, dict]] = []
    filt = os.environ.get("LINT_TEST_FILTER")
    if not LINT_TESTS_ROOT.exists():
        return tests
    for item in sorted(LINT_TESTS_ROOT.iterdir()):
        if not item.is_dir():
            continue
        expected_file = item / "_expected.json"
        readme_file = item / "readme.qmd.md"
        if not (expected_file.exists() and readme_file.exists()):
            continue
        if filt and filt not in item.name:
            continue
        with open(expected_file) as f:
            expected = json.load(f)
        tests.append((item.name, item, expected))
    return tests


def _key(issue: dict, identity: str = "object") -> tuple[str, str, str, str, str]:
    """Structural identity of an issue (message excluded), matching Issue.key().

    ``identity`` selects which id column carries the blame: the concise ``object`` id or
    qmdc's unambiguous ``global_id``.
    """
    return (
        issue.get("severity", ""),
        issue.get("code", ""),
        issue.get(identity, ""),
        issue.get("field", ""),
        issue.get("detail", ""),
    )


LINT_TESTS = find_lint_tests()


@pytest.mark.parametrize(
    "test_name,case_path,expected",
    LINT_TESTS,
    ids=[t[0] for t in LINT_TESTS],
)
def test_lint_case(test_name: str, case_path: Path, expected: dict):
    """The linter's issue set must match _expected.json exactly (order-independent)."""
    issues = lint_workspace(case_path, enforce_workspace_contract=False)
    entries = expected.get("issues", [])

    # Each expected entry declares its own identity column; an issue matches when it agrees
    # on the column that entry pinned, so one case may mix concise and global ids.
    wanted_local = {_key(e) for e in entries if "global_id" not in e}
    wanted_global = {_key(e, "global_id") for e in entries if "global_id" in e}
    actual_local = {_key(i.__dict__) for i in issues}
    actual_global = {_key(i.__dict__, "global_id") for i in issues}

    missing = sorted((wanted_local - actual_local) | (wanted_global - actual_global))
    extra = sorted(_key(i.__dict__) for i in issues
                   if _key(i.__dict__) not in wanted_local
                   and _key(i.__dict__, "global_id") not in wanted_global)
    assert not missing and not extra, (
        f"[{test_name}] linter output does not match _expected.json\n"
        f"  missing (expected, not emitted): {missing}\n"
        f"  extra   (emitted, not expected): {extra}"
    )


def _update_expected() -> None:
    """Regenerate every _expected.json from current linter output (manual review only)."""
    for item in sorted(LINT_TESTS_ROOT.iterdir()):
        if not item.is_dir() or not (item / "readme.qmd.md").exists():
            continue
        expected_file = item / "_expected.json"
        by_global = False
        if expected_file.exists():
            with open(expected_file) as f:
                previous = json.load(f).get("issues", [])
            by_global = any("global_id" in e for e in previous)
        issues = lint_workspace(item, enforce_workspace_contract=False)
        payload = []
        for i in issues:
            d = {"severity": i.severity, "code": i.code}
            if by_global:
                d["global_id"] = i.global_id
            elif i.object:
                d["object"] = i.object
            if i.field:
                d["field"] = i.field
            if i.detail:
                d["detail"] = i.detail
            payload.append(d)
        payload.sort(key=lambda d: (d.get("code", ""), d.get("object", ""),
                                    d.get("global_id", ""), d.get("field", ""),
                                    d.get("detail", "")))
        expected_file.write_text(json.dumps({"issues": payload}, indent=2) + "\n")
        print(f"updated {item.name}: {len(payload)} issue(s)"
              f"{' [global ids]' if by_global else ''}")


if __name__ == "__main__":
    if "--update" in sys.argv:
        _update_expected()
    else:
        raise SystemExit("run via pytest, or pass --update to regenerate expected files")
