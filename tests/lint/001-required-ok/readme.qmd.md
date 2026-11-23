# Required OK [[req_ok: __Workspace]]

- description: A KindSchema with required fields; the object supplies them all → lints clean

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title, capacity]
- optional: [desc]

## Morning Workshop [[w1: Workshop]]

- title: Intro to QMD
- capacity: 20
- desc: A gentle start
