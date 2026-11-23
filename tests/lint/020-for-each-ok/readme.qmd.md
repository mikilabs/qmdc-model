# For-Each OK [[fe_ok: __Workspace]]

- description: A for_each LintRule that holds for every object in scope → clean

## Session Schema [[schema_session: KindSchema]]

- kind: Session
- required: [title]

## Session Needs Speaker [[rule_speaker: LintRule]]

- for_each: Session
- assert: count('speakers') >= 1
- severity: error
- message: session {id} must reference at least one speaker

## Keynote [[s1: Session]]

- title: Opening Keynote
- speakers: [[#p1]]

## Facilitator Ann [[p1: Person]]

- name: Ann
