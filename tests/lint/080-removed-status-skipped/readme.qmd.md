# Removed Lifecycle Skipped [[rem: __Workspace]]

- description: An object with lifecycle "removed" is not checked, even if it violates its KindSchema → clean

## Workshop Schema [[schema_workshop: KindSchema]]

- kind: Workshop
- required: [title, capacity]

## Retired Workshop [[w1: Workshop]]

- lifecycle: removed
- title: Retired
