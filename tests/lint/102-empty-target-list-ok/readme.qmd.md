# Empty Target List [[empty_target: __Workspace]]

## Team Schema [[schema_team: KindSchema]]

- kind: Team

## Service Schema [[schema_service: KindSchema]]

- kind: Service
- optional: [owner]

### Field Constraints [[constraints: FieldConstraints]]

- owner: [[#schema_team]]

## Unowned Service [[svc: Service]]

- owner: []
