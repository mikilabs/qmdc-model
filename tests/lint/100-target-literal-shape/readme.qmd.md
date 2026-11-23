# Target Value Shape [[target_shape: __Workspace]]

## Team Schema [[schema_team: KindSchema]]

- kind: Team

## Service Schema [[schema_service: KindSchema]]

- kind: Service
- required: [owner]

### Field Constraints [[constraints: FieldConstraints]]

- owner: [[#schema_team]]

## Escaping Service [[svc: Service]]

- owner: platform
