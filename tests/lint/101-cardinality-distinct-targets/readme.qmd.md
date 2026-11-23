# Distinct Target Cardinality [[distinct_card: __Workspace]]

## Person Schema [[schema_person: KindSchema]]

- kind: Person

## Contract Schema [[schema_contract: KindSchema]]

- kind: Contract
- required: [participants]

### Cardinality [[cardinality: Cardinality]]

#### participants [[participants: FieldCardinality]]

- min_count: 2
- max_count: 2

## Alice [[alice: Person]]

- name: Alice

## Duplicate Participant [[c1: Contract]]

- participants: [[[#alice]], [[#alice]]]
