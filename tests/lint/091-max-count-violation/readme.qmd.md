# Max Count [[mxn: __Workspace]]

- description: A Duo schema DECLARES a maximum of 2 members; the Duo below has three, so the linter must emit max_count_violation. Cardinality is declared as one constraint object per constrained field: the object id IS the field name (`members`), and `max_count` is a plain integer field on it — no key-name parsing.

## Duo Schema [[schema_duo: KindSchema]]

- kind: Duo
- required: [members]

### Cardinality [[cardinality: Cardinality]]

#### members [[members: FieldCardinality]]

- max_count: 2

## Crowded Duo [[d1: Duo]]

- members: [[#alice]], [[#bob]], [[#carol]]

## Alice [[alice: Person]]

- name: Alice

## Bob [[bob: Person]]

- name: Bob

## Carol [[carol: Person]]

- name: Carol
