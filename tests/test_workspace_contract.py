"""Managed-workspace guarantees beyond individual constraint fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model.cli import main  # noqa: E402
from qmdc_model.linter import lint_workspace  # noqa: E402


def _init(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    assert main(["init", str(ws)]) == 0
    return ws


def test_missing_vendored_metaschema_is_a_loud_error(tmp_path: Path):
    ws = _init(tmp_path)
    (ws / "_metamodel" / "metaschema.vendor.qmd.md").unlink()

    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["missing_metaschema"]
    assert "qmdc-model upgrade" in issues[0].message


def test_observed_domain_kind_without_schema_is_a_loud_error(tmp_path: Path):
    ws = _init(tmp_path)
    (ws / "things.qmd.md").write_text(
        "# Things\n\n## Typo Kind [[w1: Widgett]]\n\n- name: x\n",
        encoding="utf-8",
    )

    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["missing_kind_schema"]
    assert issues[0].detail == "Widgett"
    assert issues[0].file == "things.qmd.md"


def test_kind_schema_closes_the_coverage_error(tmp_path: Path):
    ws = _init(tmp_path)
    (ws / "things.qmd.md").write_text(
        "# Things\n\n## Widget [[w1: Widget]]\n\n- name: x\n",
        encoding="utf-8",
    )
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write("\n## Widget [[schema_widget: KindSchema]]\n\n- kind: Widget\n- required: [name]\n")

    assert lint_workspace(ws) == []


def test_rule_config_defect_is_not_reported_twice(tmp_path: Path):
    ws = _init(tmp_path)
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write(
            "\n## Bad Rule [[rule_bad: LintRule]]\n\n"
            "- for_each: KindSchema\n"
            "- global: true\n"
            "- assert: 1 == 1\n"
            "- severity: error\n"
            "- message: bad selector count\n"
        )

    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["rule_selector_conflict"]


def test_nonexistent_workspace_never_passes(tmp_path: Path):
    issues = lint_workspace(tmp_path / "does-not-exist")
    assert [i.code for i in issues] == ["workspace_not_found"]


def test_existing_empty_directory_never_passes(tmp_path: Path):
    ws = tmp_path / "empty"
    ws.mkdir()
    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["workspace_empty"]


def test_schema_coverage_does_not_depend_on_metamodel_namespace_id(tmp_path: Path):
    ws = tmp_path / "ws"
    (ws / "_metamodel").mkdir(parents=True)
    (ws / "readme.qmd.md").write_text("# W [[w: __Workspace]]\n", encoding="utf-8")
    (ws / "_metamodel" / "readme.qmd.md").write_text(
        "# Misnamed [[metamodel: __Namespace]]\n\n"
        "## Service [[schema_service: KindSchema]]\n\n- kind: Service\n- required: [owner]\n",
        encoding="utf-8",
    )
    (ws / "model.qmd.md").write_text(
        "# Model\n\n## Good [[a: Service]]\n\n- owner: platform\n\n"
        "## Typo [[b: Servcie]]\n\n- anything: goes\n",
        encoding="utf-8",
    )

    codes = [i.code for i in lint_workspace(ws)]
    assert "missing_metaschema" in codes
    assert "missing_kind_schema" in codes


def test_dunder_prefixed_kind_typo_is_not_a_system_kind(tmp_path: Path):
    ws = _init(tmp_path)
    (ws / "model.qmd.md").write_text(
        "# Model\n\n## Typo [[b: __Servcie]]\n\n- anything: goes\n",
        encoding="utf-8",
    )
    issues = lint_workspace(ws)
    assert [(i.code, i.detail) for i in issues] == [("missing_kind_schema", "__Servcie")]


def test_non_string_kindschema_kind_is_a_clean_config_error(tmp_path: Path):
    ws = _init(tmp_path)
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write("\n## Bad [[schema_bad: KindSchema]]\n\n- kind: [Service, Team]\n")
    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["schema_bad_kind"]
    assert issues[0].file == "_metamodel/readme.qmd.md"


def test_retired_rule_is_disclosed_and_its_config_is_still_validated(tmp_path: Path):
    ws = _init(tmp_path)
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write(
            "\n## Retired Broken Rule [[old: LintRule]]\n\n"
            "- lifecycle: removed\n"
            "- for_each: NoSuchKind\n"
            "- for_each_with: marker\n"
            "- assert: true\n"
            "- severity: critical\n"
            "- message: 42\n"
        )
    codes = {i.code for i in lint_workspace(ws)}
    assert codes == {
        "retired_rule", "rule_bad_severity", "rule_bad_message",
        "rule_selector_conflict", "rule_eval_failed",
    }


def test_diagnostics_disambiguate_same_local_id_in_two_namespaces(tmp_path: Path):
    ws = tmp_path / "ws"
    (ws / "left").mkdir(parents=True)
    (ws / "right").mkdir()
    (ws / "readme.qmd.md").write_text(
        "# W [[w: __Workspace]]\n\n"
        "## Schema [[schema_service: KindSchema]]\n\n- kind: Service\n- required: [name]\n\n"
        "## Rule [[rule_fail: LintRule]]\n\n- for_each: Service\n- assert: 1 == 0\n"
        "- severity: error\n- message: failed {id}\n",
        encoding="utf-8",
    )
    for namespace in ("left", "right"):
        (ws / namespace / "readme.qmd.md").write_text(
            f"# {namespace} [[{namespace}: __Namespace]]\n\n"
            "## Service [[same: Service]]\n\n- name: One\n",
            encoding="utf-8",
        )

    failures = [i for i in lint_workspace(ws) if i.code == "rule_failed"]
    assert len(failures) == 2
    assert {i.object for i in failures} == {"same"}
    assert len({i.global_id for i in failures}) == 2
    assert len({i.key() for i in failures}) == 2


def test_empty_rule_scope_is_disclosed(tmp_path: Path):
    ws = _init(tmp_path)
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write(
            "\n## Future Schema [[schema_future: KindSchema]]\n\n- kind: Future\n\n"
            "## Future Rule [[future_rule: LintRule]]\n\n- for_each: Future\n"
            "- assert: 1 == 1\n- severity: error\n- message: future\n"
        )
    issues = lint_workspace(ws)
    assert [(i.severity, i.code) for i in issues] == [("info", "rule_empty_scope")]


def test_cli_nonexistent_workspace_never_prints_passed(tmp_path: Path, capsys):
    missing = tmp_path / "wrong-path"
    assert main(["lint", str(missing)]) == 1
    out = capsys.readouterr().out
    assert "[workspace_not_found]" in out
    assert "Lint PASSED" not in out


def test_retired_schema_is_disclosed_but_does_not_claim_kind(tmp_path: Path):
    ws = _init(tmp_path)
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write(
            "\n## Old Widget [[schema_widget: KindSchema]]\n\n"
            "- kind: Widget\n- required: [name]\n- lifecycle: removed\n"
        )
    (ws / "model.qmd.md").write_text(
        "# Model\n\n## Widget [[w1: Widget]]\n\n- name: One\n",
        encoding="utf-8",
    )
    issues = lint_workspace(ws)
    assert {i.code for i in issues} == {"missing_kind_schema", "retired_schema"}
    coverage = next(i for i in issues if i.code == "missing_kind_schema")
    assert "only retired KindSchema(s) exist: schema_widget" in coverage.message


def test_symlinked_qmd_source_is_refused_before_parse(tmp_path: Path):
    ws = _init(tmp_path)
    outside = tmp_path / "outside.qmd.md"
    outside.write_text("# Outside [[leak: Secret]]\n", encoding="utf-8")
    (ws / "linked.qmd.md").symlink_to(outside)

    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["source_symlink"]
    assert issues[0].file == "linked.qmd.md"
    assert str(outside) in issues[0].message


def test_case_variant_qmd_extension_is_not_silently_ignored(tmp_path: Path):
    ws = _init(tmp_path)
    (ws / "UPPER.QMD.MD").write_text("# Upper [[u: UnknownKind]]\n", encoding="utf-8")
    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["source_bad_extension"]
    assert issues[0].file == "UPPER.QMD.MD"


def test_qmd_like_directory_name_does_not_mask_real_errors(tmp_path: Path):
    ws = _init(tmp_path)
    (ws / "BUNDLE.QMD.MD").mkdir()
    with (ws / "_metamodel" / "readme.qmd.md").open("a", encoding="utf-8") as f:
        f.write(
            "\n## Widget [[schema_widget: KindSchema]]\n\n- kind: Widget\n- required: [color]\n\n"
            "### Field Constraints [[constraints: FieldConstraints]]\n\n- color: [red]\n"
        )
    (ws / "model.qmd.md").write_text(
        "# Model\n\n## Widget [[w1: Widget]]\n\n- color: BAD\n", encoding="utf-8")

    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["enum_violation"]


def test_symlinked_directory_is_disclosed_without_traversal(tmp_path: Path):
    ws = _init(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "ghost.qmd.md").write_text("# Ghost [[g: Secret]]\n", encoding="utf-8")
    (ws / "linked").symlink_to(outside, target_is_directory=True)

    issues = lint_workspace(ws)
    assert [i.code for i in issues] == ["source_symlink"]
    assert issues[0].file == "linked"
