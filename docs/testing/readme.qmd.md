# Testing [[testing: __Namespace]]

- version: 0.1
- description: Data-driven test engine for the metamodel linter

Linter tests are data-driven, mirroring how qmdc tests its parser: test inputs are
files, a thin runner reads them, runs the linter, and compares its structured output
to an expected file. Adding a test means adding data — no code changes. Comparison is
by structure (issue code + object + field), never by message text.

## Anchor Kinds [[anchor_kinds: text]]

| kind      | definition                                             |
| --------- | ------------------------------------------------------ |
| TestSuite | A data-driven collection of test cases with one runner  |

## TestSuite [[schema_testsuite: KindSchema]]

- kind: TestSuite
- required: [location, format, is_data_driven]
- optional: [fixtures, runner, desc]

### Description [[description: text]]

A collection of test cases discovered by glob and executed by one runner. `location`
holds the cases, `fixtures` holds shared input workspaces, `format` names the on-disk
convention.

### Field Constraints [[constraints: FieldConstraints]]

- is_data_driven: [true, false]

## Lint Tests [[suite_lint_tests: TestSuite]]

- location: tests/lint/
- fixtures: tests/fixtures/
- format: Directory workspace + _expected.json (structural issues)
- is_data_driven: true
- runner: tests/test_lint.py
- desc: One directory per case; each is a mini QMD workspace exercising one check

## How Tests Run [[how_tests_run: NarrativeDoc]]

- about: [[#suite_lint_tests]]

### Case Layout [[case_layout: text]]

Each case is a directory under `tests/lint/NNN-name/`: a `readme.qmd.md` declaring a
`__Workspace` with the KindSchemas / LintRules / objects under test, optionally more
`.qmd.md` files, and an `_expected.json`. Shared/reused input workspaces live in
`tests/fixtures/` and are referenced by cases that don't need bespoke input.

### Expected Format [[expected_format: text]]

- about: [[#linter:structural]], [[#linter:missing_required]]

`_expected.json` lists the issues the linter must emit:

```json
{ "issues": [
  {"severity": "error", "code": "missing_required", "object": "w1", "field": "name"},
  {"severity": "error", "code": "enum_violation",   "object": "w1", "field": "color"}
] }
```

An empty `issues` array is the positive case (must lint clean). The runner compares
the SET of `{severity, code, <identity>, field, detail}` tuples — order-independent.
A missing or extra issue fails the case. Message text is never compared.

`<identity>` is per entry: an entry that declares `global_id`
(`workspace:namespace:id`) is matched on qmdc's global identity, any other entry on the
concise `object` id. A case whose point is WHICH namespace is blamed must pin `global_id` —
concise ids repeat across namespaces, so with `object` alone such a case passes no matter
which of the equally-named candidates the linter named. `--update` keeps a case on global
identity once any of its entries uses it.

### Runner and Makefile [[runner_makefile: text]]

The runner globs `tests/lint/*/`, runs `lint.py --json <case>`, and diffs the issue
set against `_expected.json`. `LINT_TEST_FILTER=006` runs one case; `--update`
regenerates expected files (for manual review). A root `Makefile` target `lint-test`
runs the whole suite; `make test` runs lint-test plus workspace validation.
