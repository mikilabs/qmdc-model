# For-Each Fail [[fe_bad: __Workspace]]

- description: A for_each LintRule that fails for an object in scope → rule_failed

## Session Schema [[schema_session: KindSchema]]

- kind: Session
- required: [title]
- optional: [speakers]

## Session Needs Speaker [[rule_speaker: LintRule]]

- for_each: Session
- assert: count('speakers') >= 1
- severity: error
- message: session {id} must reference at least one speaker

## Orphan Session [[s1: Session]]

- title: Session With No Speaker
