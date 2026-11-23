# Linter [[linter: __Namespace]]

- version: 0.1
- description: The metamodel linter — what it checks and how

The linter validates a QMD workspace against its own metamodel in two phases:
(1) validate user KindSchemas/LintRules against the metaschema, then (2) validate
domain objects against those user KindSchemas and cross-object LintRules. Constraints
are declared declaratively on KindSchemas; genuinely cross-object or graph-global
invariants are LintRules. A LintRule reaches only the namespace enclosing the one it is
declared in, so a nested `a._metamodel` governs `a` while the root `_metamodel` governs
the workspace. This namespace catalogs the supported constraints and the
checks (issue codes) the linter emits — and describes its own Kinds with KindSchemas.

## Anchor Kinds [[anchor_kinds: text]]

| kind       | definition                                                        |
| ---------- | ----------------------------------------------------------------- |
| Constraint | A supported constraint component (how a rule is declared)          |
| Check      | A linter check that emits a specific issue code                    |

## Constraint [[schema_constraint: KindSchema]]

- kind: Constraint
- required: [code, expressed_as]
- optional: [shacl, declarative, status, desc]

### Description [[description: text]]

One supported constraint component. `expressed_as` says how it is written in native
QMD (a reference, a literal list, an integer, a bool, or a list of field names).
`shacl` records the SHACL Core analog it derives from. `declarative` is true when it
lives on a KindSchema (no code); false when it can only be expressed as a LintRule.

### Field Constraints [[constraints: FieldConstraints]]

- expressed_as: [reference, literal_list, integer, bool, field_list]
- declarative: [true, false]
- status: [supported, planned]

## Check [[schema_check: KindSchema]]

- kind: Check
- required: [code, severity]
- optional: [enforces, desc]

### Description [[description: text]]

One check the linter performs, identified by a stable `code` used in test expectations.
`enforces` links to the Constraint this check verifies (absent for rule/structural
checks that do not map to a single constraint).

### Field Constraints [[constraints: FieldConstraints]]

- severity: [error, warning, info]
- enforces: [[#schema_constraint]]

## Constraint Catalog

The supported constraint vocabulary. Field-level constraints live in a KindSchema's
Field Constraints child; required/optional/strict live on the KindSchema itself.

## Required [[required: Constraint]]

- code: required
- expressed_as: field_list
- shacl: sh:minCount(1)
- declarative: true
- status: supported
- desc: Listed field must be present on every object of the Kind

## Optional [[optional: Constraint]]

- code: optional
- expressed_as: field_list
- shacl: sh:minCount(0)
- declarative: true
- status: supported
- desc: Field may be present; absence is not an error

## Strict [[strict: Constraint]]

- code: strict
- expressed_as: bool
- shacl: sh:closed
- declarative: true
- status: supported
- desc: No fields beyond required+optional are allowed on the object

## Enum [[enum: Constraint]]

- code: enum
- expressed_as: literal_list
- shacl: sh:in
- declarative: true
- status: supported
- desc: Scalar field value must be one of the listed literals

## Target Kind [[target_kind: Constraint]]

- code: target_kind
- expressed_as: reference
- shacl: sh:class
- declarative: true
- status: supported
- desc: A reference field must point at an object of an allowed Kind (declared by referencing that Kind's KindSchema)

## Min Count [[min_count: Constraint]]

- code: min_count
- expressed_as: integer
- shacl: sh:minCount
- declarative: true
- status: supported
- desc: A present field must hold at least N values; e.g. participants >= 2

## Max Count [[max_count: Constraint]]

- code: max_count
- expressed_as: integer
- shacl: sh:maxCount
- declarative: true
- status: supported
- desc: A present field must hold at most N values

## Cardinality Declaration [[cardinality_declaration: NarrativeDoc]]

- about: [[#min_count]], [[#max_count]]

Cardinality is declared as one object per constrained field, nested under a
`Cardinality` child of the KindSchema: the `FieldCardinality` object's **id is the field
name**, and `min_count` / `max_count` are plain integer fields on it — no key-name
parsing, so the field name stays a real object id the graph can reference.

```markdown
## Meeting Schema [[schema_meeting: KindSchema]]

- kind: Meeting
- required: [participants]

### Cardinality [[cardinality: Cardinality]]

#### participants [[participants: FieldCardinality]]

- min_count: 2
```

A reference field counts its distinct resolved qmdc targets (duplicate references to the
same target count once); a list field counts its items; any other non-empty value counts
as one. Cardinality constrains the values a field HOLDS, not
whether the field is present — an absent field is `missing_required`'s business, so a
declared minimum on an absent optional field stays silent.

## Check Catalog

Issue codes the linter emits. Test expectations assert on these codes.

## Missing Required [[missing_required: Check]]

- code: missing_required
- severity: error
- enforces: [[#required]]
- desc: Object is missing a required field

## Unexpected Field [[unexpected_field: Check]]

- code: unexpected_field
- severity: error
- enforces: [[#strict]]
- desc: Strict Kind has a field beyond required+optional; a closed schema is a gate, not advice

## Enum Violation [[enum_violation: Check]]

- code: enum_violation
- severity: error
- enforces: [[#enum]]
- desc: Scalar value not in the allowed literal set

## Target Kind Violation [[target_kind_violation: Check]]

- code: target_kind_violation
- severity: error
- enforces: [[#target_kind]]
- desc: Reference points at an object of a disallowed Kind

## Min Count Violation [[min_count_violation: Check]]

- code: min_count_violation
- severity: error
- enforces: [[#min_count]]
- desc: A present field holds fewer values than its declared minimum

## Max Count Violation [[max_count_violation: Check]]

- code: max_count_violation
- severity: error
- enforces: [[#max_count]]
- desc: A present field holds more values than its declared maximum

## Rule Failed [[rule_failed: Check]]

- code: rule_failed
- severity: error
- desc: A LintRule assert evaluated successfully and returned false (severity taken from the rule)

## Rule Evaluation Failed [[rule_eval_failed: Check]]

- code: rule_eval_failed
- severity: error
- desc: A LintRule assert is not a string expression or raised while evaluating; this is a broken metamodel, not a domain violation

## Rule No Selector [[rule_no_selector: Check]]

- code: rule_no_selector
- severity: error
- desc: A LintRule declares no scope selector (for_each / for_each_with / global)

## Rule Bad Placement [[rule_bad_placement: Check]]

- code: rule_bad_placement
- severity: error
- desc: A LintRule is declared outside a metamodel namespace (`_metamodel` at the workspace root, `<owner>._metamodel` beneath a namespace) and outside the workspace root; placement bounds a rule's scope, so an unrecognized home is refused instead of being handed the enclosing namespace. The rule does not run

## Rule Bad Selector [[rule_bad_selector: Check]]

- code: rule_bad_selector
- severity: error
- desc: A LintRule declares an unsupported for_each* selector

## Rule Selector Conflict [[rule_selector_conflict: Check]]

- code: rule_selector_conflict
- severity: error
- desc: A LintRule declares more than one scope selector

## Rule Unknown Kind [[rule_unknown_kind: Check]]

- code: rule_unknown_kind
- severity: error
- desc: `for_each` names neither a KindSchema nor an observed Kind; likely a typo

## Rule Unknown Field [[rule_unknown_field: Check]]

- code: rule_unknown_field
- severity: error
- desc: A field helper in the assertion names no declared or observed field of its `for_each` Kind

## Rule Bad Severity [[rule_bad_severity: Check]]

- code: rule_bad_severity
- severity: error
- desc: LintRule severity is not exactly `error`, `warning`, or `info`

## Rule Bad Message [[rule_bad_message: Check]]

- code: rule_bad_message
- severity: error
- desc: LintRule message is not a non-empty string

## Rule Empty Scope [[rule_empty_scope: Check]]

- code: rule_empty_scope
- severity: info
- desc: A valid rule currently matches no domain objects, so it does not execute

## Retired Rule [[retired_rule: Check]]

- code: retired_rule
- severity: info
- desc: Rule configuration is validated and disclosed, but the retired rule does not execute

## Retired Object [[retired_object: Check]]

- code: retired_object
- severity: info
- desc: A retired domain object is disclosed and skipped by schema checks and rules

## Schema Field List [[schema_field_list: Check]]

- code: schema_field_list
- severity: error
- desc: KindSchema required/optional contains something other than field-name strings

## Schema Field Overlap [[schema_field_overlap: Check]]

- code: schema_field_overlap
- severity: error
- desc: One field is both required and optional

## Schema Bad Kind [[schema_bad_kind: Check]]

- code: schema_bad_kind
- severity: error
- desc: KindSchema kind is not one non-empty string

## Schema Bad Strict [[schema_bad_strict: Check]]

- code: schema_bad_strict
- severity: error
- desc: strict is not the QMD boolean `true` or `false` (prose such as `yes` is invalid)

## Schema Bad Child [[schema_bad_child: Check]]

- code: schema_bad_child
- severity: error
- desc: constraints/cardinality is not exactly one nested FieldConstraints/Cardinality child with that literal id

## Schema Bad Placement [[schema_bad_placement: Check]]

- code: schema_bad_placement
- severity: error
- desc: FieldConstraints/Cardinality/FieldCardinality is not nested under its expected parent Kind

## Schema Bad Target Kind [[schema_bad_target_kind: Check]]

- code: schema_bad_target_kind
- severity: error
- desc: A target_kind constraint points at something other than a KindSchema

## Schema Unknown Field Constraint [[schema_unknown_field_constraint: Check]]

- code: schema_unknown_field_constraint
- severity: error
- desc: FieldConstraints or Cardinality names no required/optional field of its KindSchema

## Schema Empty Constraint [[schema_empty_constraint: Check]]

- code: schema_empty_constraint
- severity: error
- desc: FieldConstraints entry declares neither a literal enum list nor a KindSchema reference

## Duplicate Kind Schema [[duplicate_kind_schema: Check]]

- code: duplicate_kind_schema
- severity: error
- desc: More than one KindSchema claims the same Kind; neither is enforced until ownership is unique. One diagnostic per claim, at its own file and line, naming every claimant by global id — concise ids repeat across namespaces

## Constraint Value Shape [[constraint_value_shape: Check]]

- code: constraint_value_shape
- severity: error
- desc: An enum field holds references, or a target_kind field holds a literal

## Cardinality Bad Bound [[cardinality_bad_bound: Check]]

- code: cardinality_bad_bound
- severity: error
- desc: min_count/max_count is not a non-negative integer

## Cardinality Bad Range [[cardinality_bad_range: Check]]

- code: cardinality_bad_range
- severity: error
- desc: min_count is greater than max_count

## Cardinality Bad Shape [[cardinality_bad_shape: Check]]

- code: cardinality_bad_shape
- severity: error
- desc: A bound is inline on Cardinality or its FieldCardinality child declares no bound

## Missing Metaschema [[missing_metaschema: Check]]

- code: missing_metaschema
- severity: error
- desc: An initialized workspace is missing one or more vendored base meta-kinds; run upgrade

## Missing Kind Schema [[missing_kind_schema: Check]]

- code: missing_kind_schema
- severity: error
- desc: An observed domain Kind has no KindSchema and would otherwise be unchecked

## Retired Schema [[retired_schema: Check]]

- code: retired_schema
- severity: info
- desc: KindSchema config is validated and disclosed, but it no longer claims/enforces its Kind

## Lifecycle Bad Value [[lifecycle_bad_value: Check]]

- code: lifecycle_bad_value
- severity: error
- desc: Reserved lifecycle field is present with anything other than exact `removed`

## Workspace Not Found [[workspace_not_found: Check]]

- code: workspace_not_found
- severity: error
- desc: The lint target does not exist or is not a directory

## Workspace Empty [[workspace_empty: Check]]

- code: workspace_empty
- severity: error
- desc: qmdc parsed no objects; an empty/wrong workspace path must never pass cleanly

## Source Unparsed [[source_unparsed: Check]]

- code: source_unparsed
- severity: error
- desc: qmdc discovered a QMD file but indexed no object from it; file omission is fail-closed

## Source Symlink [[source_symlink: Check]]

- code: source_symlink
- severity: error
- desc: A QMD source path is symlinked; lint refuses before qmdc can read outside the workspace

## Source Bad Extension [[source_bad_extension: Check]]

- code: source_bad_extension
- severity: error
- desc: A case-variant QMD extension is ignored by qmdc; rename it to lowercase `.qmd.md`

## QMDC Failed [[qmdc_failed: Check]]

- code: qmdc_failed
- severity: error
- desc: qmdc exited nonzero or returned an invalid response; parser failure is fail-closed

## Structural [[structural: Check]]

- code: structural
- severity: error
- desc: Passthrough of qmdc workspace validate errors (broken_link, duplicate_id, ...)

## How It Works [[how_it_works: NarrativeDoc]]

- about: [[#schema_constraint]], [[#schema_check]]

### Two Phases [[two_phases: text]]

- about: [[#missing_required]], [[#structural]]

Phase 0 runs `qmdc workspace validate` and surfaces structural errors as `structural`
checks. Phase 1 validates user KindSchemas and LintRules against the metaschema
(a KindSchema must declare its `kind`; a LintRule must have exactly one scope selector).
Phase 2 validates domain objects against their user KindSchemas (required, strict,
enum, target_kind) and evaluates cross-object LintRules.

### LintRule Assert Helpers [[assert_helpers: text]]

A LintRule `assert` is a boolean expression over a fixed helper vocabulary evaluated
per object in scope: `field(name)`, `has(name)`, `refs(name)`, `count(name)`,
`target(ref_field)`, `targets(ref_field)`, `kind_of(id)`, `exists(id)`,
`incoming(kind?, via?)`, `all_of(kind)`, `refs_of(obj, field)`, `id_of(obj)`,
`overlaps(left, right)`, `same_members(left, right)`, `is_subset(left, right)`. `id` is
the current object's qmdc global identity; `id_of` returns that identity for objects from
`all_of`/`target(s)`. `incoming(via=...)` filters qmdc `edge_type` (the semantic link role,
including preamble `about`), not `source_field`. References come from qmdc's resolved `edges` graph and use
global object identities, so these helpers compose across namespace boundaries (`refs()`
output can be passed straight to `exists()` or `kind_of()`). `for_each_with` scopes only
domain objects, never qmdc system/base-metamodel plumbing; `global` has no current object,
so it uses `all_of`/`refs_of` rather than `field`/`refs`. Prefer declaring a Constraint on
a KindSchema; reach for a LintRule only for cross-object or graph-global invariants (the
escape hatch).
