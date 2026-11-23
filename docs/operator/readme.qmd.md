# Model Operator [[operator: __Namespace]]

- version: 0.1
- description: The qmdc-model command surface for managing a metamodel

The operator is the tool layer over a metamodel workspace: discover Kinds and objects,
lint against the metaschema, and (later) mutate the model. Commands are namespaced
`qmdcmodel.*`. This is the broadest, least-settled artifact — most commands are planned.

## Anchor Kinds [[anchor_kinds: text]]

| kind    | definition                                            |
| ------- | ----------------------------------------------------- |
| Command | A qmdc-model operator command (`qmdcmodel.*`)          |

## Command [[schema_command: KindSchema]]

- kind: Command
- required: [name, summary]
- optional: [args, status, desc]

### Description [[description: text]]

One operator command. `name` is the invocation (`qmdcmodel.get`), `summary` is a
one-line purpose, `args` a short signature, `status` whether it exists yet.

### Field Constraints [[constraints: FieldConstraints]]

- status: [supported, planned]

## Commands

Intended operator surface; most are planned.

## Init [[cmd_init: Command]]

- name: qmdcmodel.init
- summary: Create the workspace directory if missing, scaffold its root `readme.qmd.md` (`__Workspace`) and `_metamodel` namespace, and vendor the base meta-kinds
- args: [workspace]
- status: supported

## Upgrade [[cmd_upgrade: Command]]

- name: qmdcmodel.upgrade
- summary: Re-vendor the workspace to this version — creates, rewrites and deletes the tool-owned `*.vendor.qmd.md` files, one copy per workspace (`--dry-run` prints the plan)
- args: [workspace, --dry-run]
- status: supported

## Get [[cmd_get: Command]]

- name: qmdcmodel.get
- summary: Fetch a Kind or object (schema, fields, constraints) from the metamodel
- args: <ref>
- status: planned

## Lint [[cmd_lint: Command]]

- name: qmdcmodel.lint
- summary: Validate a workspace against its metaschema and KindSchemas (two-phase)
- args: [workspace]
- status: supported

## Sop [[cmd_sop: Command]]

- name: qmdcmodel.sop
- summary: Print the metamodel-creation SOP shipped with this version (`--path` prints its path instead)
- args: [--path]
- status: supported

## Validate [[cmd_validate: Command]]

- name: qmdcmodel.validate
- summary: Structural QMD validation (broken links, duplicate ids) — wraps qmdc validate
- args: [workspace]
- status: supported

## List [[cmd_list: Command]]

- name: qmdcmodel.list
- summary: List Kinds and their instance counts in the metamodel
- args: [workspace]
- status: planned

## Viz [[cmd_viz: Command]]

- name: qmdcmodel.viz
- summary: Render the metamodel (types, fields, relations) as an HTML ER diagram
- args: [workspace, out]
- status: planned
