# Ref Not Enum [[rne: __Workspace]]

- description: Regression — a reference-valued constraint (target_kind) must NOT be treated as an enum literal set. A valid reference lints clean.

## Room Schema [[schema_room: KindSchema]]

- kind: Room

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title, room]

### Field Constraints [[constraints: FieldConstraints]]

- room: [[#schema_room]]

## Main Hall [[room1: Room]]

- name: Main Hall

## Morning Workshop [[w1: Workshop]]

- title: Intro to QMD
- room: [[#room1]]
