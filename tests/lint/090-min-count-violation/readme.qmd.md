# Min Count [[mcn: __Workspace]]

- description: A Meeting schema DECLARES a minimum of 2 participants; the Meeting below has only one, so the linter must emit min_count_violation. Cardinality is declared as one constraint object per constrained field: the object id IS the field name (`participants`), and `min_count` is a plain integer field on it — no key-name parsing.

## Meeting Schema [[schema_meeting: KindSchema]]

- kind: Meeting
- required: [participants]

### Cardinality [[cardinality: Cardinality]]

#### participants [[participants: FieldCardinality]]

- min_count: 2

## One-Person Meeting [[m1: Meeting]]

- participants: [[#alice]]

## Alice [[alice: Person]]

- name: Alice
