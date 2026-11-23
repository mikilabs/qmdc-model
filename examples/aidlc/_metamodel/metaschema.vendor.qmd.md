<!-- qmdc-model 0.3.0 — generated file owned by the tool: `qmdc-model upgrade` rewrites or deletes it. Do not edit by hand. -->

Vendored base meta-kinds (KindSchema, FieldConstraints, Cardinality, FieldCardinality,
LintRule) + phase-1 rules.
Source: qmdc-model `docs/metaschema`. This file is OWNED by the tool: `qmdc-model upgrade`
rewrites it, and deletes it outright if a later version no longer ships it — so a hand
edit here is always lost. Change `docs/metaschema` and re-vendor instead.

## KindSchema [[schema_kindschema: KindSchema]]

- kind: KindSchema
- required: [kind]
- optional: [required, optional, strict, description, constraints, cardinality]

### Description [[description: text]]

Declares the shape of one Kind: which fields are required vs optional, whether the
Kind is closed to extra fields (`strict`), and — via its nested Field Constraints
child — per-field value rules (enums as literal lists, target-Kind as references to
other KindSchema objects). `required`/`optional` are lists of field names.

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
(an `enum` constraint) or references to KindSchema objects (a `target_kind` constraint).
Open (`strict: false`); declares no fixed fields.

## Cardinality [[schema_cardinality: KindSchema]]

- kind: Cardinality
- strict: false

### Description [[description: text]]

The count-bounds container nested under a KindSchema. Each child is one
`FieldCardinality` object whose id is the constrained field's name, so this Kind declares
no fields of its own and stays open (`strict: false`).

## FieldCardinality [[schema_fieldcardinality: KindSchema]]

- kind: FieldCardinality
- optional: [min_count, max_count]
- strict: true

### Description [[description: text]]

The count bounds of exactly one field: the object's id is the field name, `min_count` /
`max_count` are plain integers. They constrain the values a present field holds — not
whether the field exists, which is what `required` covers.

## LintRule [[schema_lintrule: KindSchema]]

- kind: LintRule
- required: [severity, assert, message]
- optional: [for_each, for_each_with, global]

### Description [[description: text]]

A cross-object invariant the linter evaluates. `assert` is a boolean expression over
the linter's helper vocabulary. A rule selects its scope with exactly one of: `for_each`
(each object of one Kind), `for_each_with` (domain objects having a field; metamodel
plumbing excluded), or `global` (once, with no current object).

### Field Constraints [[constraints: FieldConstraints]]

- severity: [error, warning, info]

