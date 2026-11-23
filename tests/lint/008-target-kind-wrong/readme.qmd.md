# Target Kind Wrong [[tk_bad: __Workspace]]

- description: A reference field points at the wrong Kind → target_kind_violation

## Room Schema [[schema_room: KindSchema]]

- kind: Room

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title, room]

### Field Constraints [[constraints: FieldConstraints]]

- room: [[#schema_room]]

## Main Hall [[room1: Room]]

- name: Main Hall

## Facilitator Bob [[bob: Person]]

- name: Bob

## Morning Workshop [[w1: Workshop]]

- title: Intro to QMD
- room: [[#bob]]
