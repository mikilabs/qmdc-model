# qmdc-model

Metamodel operator and linter for [QMD](https://github.com/mikilabs/qmdc) workspaces.

`qmdc-model` operates on the **metamodel** of a QMD workspace — the schema layer
(`KindSchema`, `LintRule`) that describes and constrains your domain objects. It
scaffolds the `_metamodel` namespace and runs a two-phase lint that checks your
domain objects against their declared schemas.

## Install

```bash
uv tool install qmdc-model
```

Or, inside a project:

```bash
uv add qmdc-model
```

Requires Python 3.12+. The linter shells out to the [`qmdc`](https://github.com/mikilabs/qmdc)
CLI (`qmdc workspace parse` / `qmdc workspace validate`), which is installed as a
dependency; that bundled copy is used even if another `qmdc` is on your `PATH`.

## Usage

```bash
# Create a workspace: root readme + _metamodel namespace + vendored base meta-kinds
qmdc-model init <workspace>

# Re-vendor after updating the tool (the tool owns *.vendor.qmd.md)
qmdc-model upgrade <workspace>
qmdc-model upgrade <workspace> --dry-run

# Lint a workspace against its metaschema and KindSchemas
qmdc-model lint <workspace>

# Machine-readable output
qmdc-model lint <workspace> --json

# Print the metamodel-creation SOP shipped with this version
qmdc-model sop
qmdc-model sop --path   # its path on disk, for an agent that reads files itself
```

### `init`

Creates the workspace directory if it does not exist (parents included) and
scaffolds a workspace that lints clean out of the box:

- `readme.qmd.md` — the workspace root object, `[[<id>: __Workspace]]`. The id is
  derived from the directory name as lowercase snake_case while preserving Unicode
  letters (`my-notes` → `my_notes`, `Мой проект` → `мой_проект`); punctuation-only
  names get a stable hash suffix. The heading label keeps the name, but line breaks
  are folded and QMD declaration brackets are neutralized so a directory name cannot
  inject another object. Thin by design: name, description, pointer to the metamodel.
- `_metamodel/readme.qmd.md` — namespace skeleton where you add your own
  `KindSchema` and `LintRule` objects.
- `_metamodel/metaschema.vendor.qmd.md` — vendored base meta-kinds
  (`KindSchema`, `FieldConstraints`, `Cardinality`, `FieldCardinality`, `LintRule`) so the workspace is
  self-contained and lints offline.

It skips files that already exist, so it is safe to re-run. It refuses (exit 2)
if the target path exists and is not a directory.

### `upgrade`

`init` never overwrites, so it cannot deliver a newer metaschema to an existing
workspace — `upgrade` does. Files named `*.vendor.qmd.md` are **owned by the
tool**: upgrade creates a missing one, rewrites a stale one, and deletes one this
version no longer ships. A hand edit there is always lost; change the metamodel
in your own `_metamodel/readme.qmd.md` instead. Nothing else is touched. Symlinked
`_metamodel`/vendor paths, non-regular vendor paths and unwritable plans are refused
before the first mutation, so the ownership mask cannot escape the real workspace tree.

Each vendored file carries a marker line with the tool version that wrote it, and
staleness is decided by comparing the body with the shipped copy — so the command
is a no-op when the workspace is already current.

Vendored base meta-kinds live as **one copy per workspace**, even though
`_metamodel` namespaces may be many: they carry fixed object ids, so a second copy
makes every reference inside them ambiguous. Upgrade keeps the copy it finds
(preferring the root `_metamodel`), removes the rest, and the linter still finds it
by `__kind` from anywhere in the workspace.

```bash
qmdc-model upgrade <workspace> --dry-run   # print the plan, write nothing
```

### `lint`

Two-phase, config-driven check. It reads `KindSchema` and `LintRule` objects
from the workspace and validates domain objects against them. Checks include:

| code                    | meaning                                              |
| ----------------------- | ---------------------------------------------------- |
| `structural`            | passthrough of `qmdc workspace validate`             |
| `workspace_not_found`   | lint target is missing or not a directory             |
| `workspace_empty`       | qmdc parsed no objects from the workspace             |
| `source_unparsed`       | qmdc discovered a file but indexed no object from it  |
| `source_symlink`        | QMD source is redirected through a symlink             |
| `source_bad_extension`  | source must use lowercase `.qmd.md`                   |
| `qmdc_failed`           | qmdc failed or returned an invalid response           |
| `missing_required`      | a required field is absent                           |
| `unexpected_field`      | a `strict` Kind has a field beyond required+optional |
| `enum_violation`        | a scalar value is not in the allowed literal set     |
| `target_kind_violation` | a reference points at a disallowed Kind              |
| `min_count_violation`   | a present field holds fewer values than its minimum  |
| `max_count_violation`   | a present field holds more values than its maximum   |
| `rule_failed`           | a `LintRule` assertion returned false                |
| `rule_eval_failed`      | an assertion is invalid or raised while running      |
| `rule_no_selector`      | a `LintRule` declares no scope selector              |
| `rule_bad_placement`    | a `LintRule` lives outside a metamodel namespace     |
| `rule_bad_selector`     | a `LintRule` uses an unsupported selector            |
| `rule_selector_conflict`| a `LintRule` declares multiple selectors             |
| `rule_unknown_kind`     | `for_each` names no declared/observed Kind            |
| `rule_unknown_field`    | an assertion names no field of its selected Kind      |
| `rule_bad_severity`     | severity is not `error`, `warning`, or `info`         |
| `rule_bad_message`      | message is not a non-empty string                     |
| `rule_empty_scope`      | valid selector currently matches nothing (info)      |
| `retired_rule`          | rule is validated and disclosed but not executed     |
| `retired_object`        | domain object is disclosed but skipped (info)        |
| `schema_field_list`     | required/optional contains a non-field-name value     |
| `schema_field_overlap`  | one field is both required and optional               |
| `schema_bad_kind`       | KindSchema kind is not one non-empty string           |
| `schema_bad_strict`     | strict is not QMD boolean `true`/`false`              |
| `schema_bad_child`      | constraints/cardinality is not one expected child     |
| `schema_bad_placement`  | schema helper object has the wrong qmdc parent         |
| `schema_bad_target_kind`| target_kind points at something other than KindSchema|
| `schema_unknown_field_constraint`| constraint names no required/optional field |
| `schema_empty_constraint`| FieldConstraints entry has no enum/reference value    |
| `duplicate_kind_schema` | more than one KindSchema claims a Kind                |
| `constraint_value_shape`| value switches enum/reference representation         |
| `cardinality_bad_bound` | a count bound is not a non-negative integer           |
| `cardinality_bad_range` | `min_count` is greater than `max_count`               |
| `cardinality_bad_shape` | a bound is not in a FieldCardinality child            |
| `missing_metaschema`    | an initialized workspace lost its base meta-kinds     |
| `missing_kind_schema`   | an observed domain Kind has no KindSchema             |
| `retired_schema`        | schema is validated/disclosed but no longer enforced  |
| `lifecycle_bad_value`   | lifecycle is not the exact reserved value `removed`   |

`lint` exits non-zero when any `error`-severity issue is found, so it drops
straight into CI.

A `LintRule` reaches only the namespace **enclosing** the one it is declared in: a rule in
a nested `foo/_metamodel` judges `foo` and its descendants, a rule in the workspace root
`_metamodel` judges everything. Those are the only two shapes available, because a rule
must live in a metamodel namespace (or the workspace root) — anywhere else is
`rule_bad_placement` and the rule does not run, so a renamed or stray home fails loudly
instead of silently handing the rule the whole workspace. The bound covers the objects
judged, the field names the assert may reference and what `all_of()` enumerates; reference
traversal (`refs`/`target`/`incoming`) stays global, since evidence may come from anywhere.
So an extension cannot redden a project's lint on a sibling extension's data, and a
workspace-wide rule is expressed by placing it in the root metamodel rather than by a flag.

### `sop`

Prints the metamodel-creation procedure that ships **inside this package**
([`src/qmdc_model/sop/sop-metamodel-creation.md`](src/qmdc_model/sop/sop-metamodel-creation.md)),
so an agent working in any repository can obtain the version that matches the
installed checks:

```bash
qmdc-model sop            # the procedure on stdout
qmdc-model sop --path     # its path, for an agent that reads files itself
```

There is deliberately one copy, distributed with the tool. The procedure is
version-locked to the constraint vocabulary the linter enforces, so a copy
committed into each project would silently fall behind it.

## Development

```bash
# Install dev dependencies
uv sync

# Run the test suite (data-driven linter cases under tests/lint/)
make test
# or
uv run pytest -q
```

See [`docs/`](docs/) for reference material on the linter, metaschema, and
operator; run `qmdc-model sop` for the full step-by-step procedure for authoring
a metamodel.

## Releasing

The version lives only in `pyproject.toml`; the package reads it from its
installed metadata. CI (`.github/workflows/ci.yml`) runs the tests and a wheel
smoke test on Linux, macOS and Windows for every push to `main` and every PR.

```bash
make bump-patch        # or bump-minor / bump-major; also refreshes uv.lock
git commit -am "chore(release): bump qmdc-model to X.Y.Z"
git push origin main
git tag vX.Y.Z && git push origin vX.Y.Z
```

The tag starts `.github/workflows/release.yml`: it runs the full CI matrix,
checks that the tag matches the `pyproject.toml` version, builds, and publishes to
PyPI. It authenticates with PyPI Trusted Publishing (environment `pypi`), or with
a `UV_PUBLISH_TOKEN` repository secret if one is set. Files already on PyPI are
skipped, so re-running a release is safe.

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).
