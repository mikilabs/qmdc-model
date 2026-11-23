# Strict Extra Field [[strict_bad: __Workspace]]

- description: A strict KindSchema whose object carries a field beyond required+optional → error-level unexpected_field

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title]
- optional: [desc]
- strict: true

## Morning Workshop [[w1: Workshop]]

- title: Intro to QMD
- desc: A gentle start
- capacity: 20
