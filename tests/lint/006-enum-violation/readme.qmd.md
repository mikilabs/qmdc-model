# Enum Violation [[enum_bad: __Workspace]]

- description: A scalar field value outside the enum literal set → enum_violation

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title, level]

### Field Constraints [[constraints: FieldConstraints]]

- level: [beginner, intermediate, advanced]

## Morning Workshop [[w1: Workshop]]

- title: Intro to QMD
- level: expert
