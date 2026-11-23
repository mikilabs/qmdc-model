# Missing Identity [[missing_identity: __Workspace]]

## Service Schema [[schema_service: KindSchema]]

- kind: Service
- optional: [owner, reviewer]

## Identity Rule [[rule_identity: LintRule]]

- for_each: Service
- assert: id_of(target('owner')) != id_of(target('reviewer'))
- severity: error
- message: owner and reviewer must differ

## Service [[svc: Service]]

- name: One
