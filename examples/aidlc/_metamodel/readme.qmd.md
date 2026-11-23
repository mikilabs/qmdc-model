# Metamodel [[_metamodel: __Namespace]]

- description: Schema layer for the AI-DLC experiments workspace — Kinds, field constraints, and cross-object rules

Recommended convention: a workspace keeps its metamodel (KindSchemas + LintRules) in a
`_metamodel/` folder as the `_metamodel` namespace, separate from domain objects
(Runs, Engines, ...) which live in the workspace root and other namespaces.

## Metamodel Schema [[schema_metamodel: KindSchema]]

- kind: Metamodel
- optional: [anchor_kinds]

## Metamodel [[metamodel: Metamodel]]

### Anchor Kinds [[anchor_kinds: text]]

| kind    | definition                                                            |
| ------- | --------------------------------------------------------------------- |
| Engine  | Stock AI-DLC build pinned at a commit                                  |
| Overlay | Named, reusable set of changes applied on top of the engine           |
| Target  | Target brownfield repository pinned at a commit                        |
| Task    | Unit of work (usually a real issue) run against a Target              |
| Run     | One execution: engine + target + task + overlays, up to a stage; holds metrics |

## Engine [[schema_engine: KindSchema]]

- kind: Engine
- required: [repo, commit, branch]

### Description [[description: text]]

Stock AI-DLC build from the aidlc-workflows repo, frozen at a commit for
reproducibility. Usually constant within a study; becomes a variable only when
comparing engine versions.

## Overlay [[schema_overlay: KindSchema]]

- kind: Overlay
- required: [role]
- optional: [requires]

### Description [[description: text]]

A named, reusable change set layered on the engine: connect an MCP server, rewrite a
stage's behavior, add tools to an agent. Lives in its own catalog, reused across Runs.
`requires` declares an external precondition (e.g. a target's codekb_index_id) checked
at run-prep, not modeled as a separate entity.

## Target [[schema_target: KindSchema]]

- kind: Target
- required: [repo, commit]
- optional: [codekb_index_id]

### Description [[description: text]]

Real brownfield repository pinned at a commit. Reusable across many tasks and runs.
`codekb_index_id` is stored only when the index was built on the same commit —
code commit and index commit must match or comparisons lie.

## Task [[schema_task: KindSchema]]

- kind: Task
- required: [target, description]

### Description [[description: text]]

The work the AI-DLC workflow is born with, usually from a real issue. Belongs to a
Target (an issue is filed against a repo); one Target can have many Tasks.

### Field Constraints [[constraints: FieldConstraints]]

- target: [[#schema_target]]

## Run [[schema_run: KindSchema]]

- kind: Run
- required: [engine, target, task, stage, status]
- optional: [overlays, budget, repeats, reached_gate, moves, tokens, duration_s, artifacts_count, remarks_count]

### Description [[description: text]]

The central object: one live execution binding an Engine, a Target, a Task, and zero
or more Overlays, carried up to a chosen stage gate. Non-deterministic, so a
combination is run several times. Metrics are captured as fields on the Run.
Versioned inputs (engine/target/task/overlays) stay separate from ephemeral outputs
(working copy, artifacts, trace) which live outside the model.

### Field Constraints [[constraints: FieldConstraints]]

- engine: [[#schema_engine]]
- target: [[#schema_target]]
- task: [[#schema_task]]
- overlays: [[#schema_overlay]]
- stage: [requirements, user_stories, application_design, units_generation, functional_design, nfr_assessment, nfr_design, infrastructure_design, code_generation, reverse_engineering]
- status: [planned, running, done, failed]
- reached_gate: [true, false]

## Rules [[rules: [LintRule]]]

Cross-object invariants beyond per-field schema — an array of rules, no individual names.

| severity | for_each | assert                                            | message                                            |
| -------- | -------- | ------------------------------------------------- | -------------------------------------------------- |
| error    | Run      | refs_of(target("task"), "target") == refs("target") | Run '{id}' task does not belong to the run's target |
| warning  | Overlay  | len(incoming()) > 0                               | Overlay '{id}' is not used by any run              |
