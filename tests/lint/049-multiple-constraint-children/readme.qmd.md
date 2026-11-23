# Multiple Constraint Children [[multi_constraints: __Workspace]]

## Person Schema [[schema_person: KindSchema]]

- kind: Person

## Contract Schema [[schema_contract: KindSchema]]

- kind: Contract
- optional: [status, participant]

### Field Constraints [[constraints: [FieldConstraints]]]

#### First [[first]]

- status: [planned, active]

#### Second [[second]]

- participant: [[#schema_person]]
