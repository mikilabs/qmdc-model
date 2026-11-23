# Max Count Satisfied [[mxo: __Workspace]]

- description: The same Duo schema declaring a maximum of 2 members, given a Duo that holds exactly 2. The boundary value satisfies the maximum, so the linter must stay silent.

## Duo Schema [[schema_duo: KindSchema]]

- kind: Duo
- required: [members]

### Cardinality [[cardinality: Cardinality]]

#### members [[members: FieldCardinality]]

- max_count: 2

## Proper Duo [[d1: Duo]]

- members: [[#alice]], [[#bob]]

## Alice [[alice: Person]]

- name: Alice

## Bob [[bob: Person]]

- name: Bob
