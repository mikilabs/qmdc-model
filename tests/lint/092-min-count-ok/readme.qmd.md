# Min Count Satisfied [[mco: __Workspace]]

- description: The same Meeting schema declaring a minimum of 2 participants, given a Meeting that holds exactly 2. The boundary value satisfies the minimum, so the linter must stay silent.

## Meeting Schema [[schema_meeting: KindSchema]]

- kind: Meeting
- required: [participants]

### Cardinality [[cardinality: Cardinality]]

#### participants [[participants: FieldCardinality]]

- min_count: 2

## Two-Person Meeting [[m1: Meeting]]

- participants: [[#alice]], [[#bob]]

## Alice [[alice: Person]]

- name: Alice

## Bob [[bob: Person]]

- name: Bob
