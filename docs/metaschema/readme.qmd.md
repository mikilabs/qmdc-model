# Metaschema [[metaschema: __Namespace]]

- version: 0.1
- description: Vendored schema-for-schema — defines what a valid KindSchema and LintRule look like

Self-describing metamodel layer (analogous to "SHACL for SHACL"). The linter runs in
two phases: (1) validate user KindSchemas/LintRules against this metaschema, then
(2) validate domain objects against the user KindSchemas. This namespace is vendored
and versioned together with the linter — the pair defines the supported constraint
vocabulary.

## Meta Kinds [[meta_kinds: text]]

| kind             | definition                                                   |
| ---------------- | ------------------------------------------------------------ |
| KindSchema       | Describes the fields and constraints allowed on a Kind        |
| FieldConstraints | Per-field value rules (enum / target-Kind) attached to a KindSchema |
| Cardinality      | Container for the per-field count bounds of a KindSchema       |
| FieldCardinality | The min_count / max_count bounds of one field                  |
| LintRule         | A cross-object invariant checked by the linter                |

## KindSchema [[schema_kindschema: KindSchema]]

- kind: KindSchema
- required: [kind]
- optional: [required, optional, strict, description, constraints, cardinality]

### Description [[description: text]]

Declares the shape of one Kind: which fields are required vs optional, whether the
Kind is closed to extra fields (`strict`), and — via its nested Field Constraints
child — per-field value rules (enums as literal lists, target-Kind as references to
other KindSchema objects). `required`/`optional` are lists of field names (not
references). A KindSchema is itself an instance of Kind "KindSchema" (self-describing).

### Field Constraints [[constraints: FieldConstraints]]

- strict: [true, false]
- constraints: [[#schema_fieldconstraints]]
- cardinality: [[#schema_cardinality]]

## FieldConstraints [[schema_fieldconstraints: KindSchema]]

- kind: FieldConstraints
- strict: false

### Description [[description: text]]

The per-field constraint bag nested under a KindSchema. Its keys are dynamic — each
key is a field name of the described Kind, and its value is either a literal list
(an `enum` constraint) or one or more references to KindSchema objects (a `target_kind`
constraint). Because keys vary per Kind, this Kind is open (`strict: false`) and
declares no fixed fields.

## Cardinality [[schema_cardinality: KindSchema]]

- kind: Cardinality
- strict: false

### Description [[description: text]]

The count-bounds container nested under a KindSchema. It declares no fields of its own —
each child is one `FieldCardinality` object whose id is the constrained field's name — so
this Kind is open (`strict: false`).

## FieldCardinality [[schema_fieldcardinality: KindSchema]]

- kind: FieldCardinality
- optional: [min_count, max_count]
- strict: true

### Description [[description: text]]

The count bounds of exactly one field: the object's **id is the field name**, and
`min_count` / `max_count` are plain integers on it. Both are optional (declare one or
both), and they constrain the values a present field holds — not whether the field
exists, which is what `required` covers.

## LintRule [[schema_lintrule: KindSchema]]

- kind: LintRule
- required: [severity, assert, message]
- optional: [for_each, for_each_with, global]

### Description [[description: text]]

A cross-object invariant the linter evaluates. `assert` is a boolean expression over
the linter's helper vocabulary (`field`, `has`, `refs`, `count`, `target`, `targets`,
`kind_of`, `exists`, `incoming`, `all_of`, `refs_of`, `id_of`, `overlaps`,
`same_members`, `is_subset`). A rule selects its scope with
exactly one of: `for_each` (each object of a Kind), `for_each_with` (each domain object
having a field; system/base-metamodel objects are excluded), `global` (once, with no
current object). A rule judges the namespace ENCLOSING the one it is declared in — a
nested `a._metamodel` rule reaches `a` and its descendants, a root `_metamodel` rule the
whole workspace — and that bound covers the judged objects, the field names the assert may
name and `all_of()`; reference traversal stays global. A rule declared outside a metamodel
namespace (and outside the workspace root) is `rule_bad_placement` and does not run, so
those two scopes are the only ones reachable. Prefer declaring constraints in a
KindSchema; use a LintRule only for genuinely cross-object or graph-global checks.

### Field Constraints [[constraints: FieldConstraints]]

- severity: [error, warning, info]

## Phase-1 Validation [[phase_one: text]]

The linter validates this configuration layer directly before evaluating domain rules:
required KindSchema fields, exactly one supported LintRule selector, safe string assertion,
known Kind/field, severity and message. These checks have dedicated issue codes and source
locations; expressing them again as LintRules would duplicate every diagnostic.
