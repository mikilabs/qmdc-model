# Metamodel [[_metamodel: __Namespace]]

## Environment Schema [[schema_environment: KindSchema]]

- kind: Environment

## Pipeline Schema [[schema_pipeline: KindSchema]]

- kind: Pipeline

## Deployment Schema [[schema_deployment: KindSchema]]

- kind: Deployment
- required: [environment]

### Field Constraints [[constraints: FieldConstraints]]

- environment: [[#schema_environment]]
