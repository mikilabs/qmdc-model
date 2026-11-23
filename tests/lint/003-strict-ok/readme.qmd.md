# Strict OK [[strict_ok: __Workspace]]

- description: A strict KindSchema whose object uses only required+optional fields → clean

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title]
- optional: [desc]
- strict: true

## Morning Workshop [[w1: Workshop]]

- title: Intro to QMD
- desc: A gentle start
