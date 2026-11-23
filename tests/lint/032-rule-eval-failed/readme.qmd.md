# Assert Evaluation Failure [[eval_fail: __Workspace]]

## Session Schema [[schema_session: KindSchema]]

- kind: Session
- required: [title]

## Session [[s1: Session]]

- title: Test

## Broken Rule [[rule_broken: LintRule]]

- for_each: Session
- assert: incoming() > 0
- severity: error
- message: session {id} has no incoming references
