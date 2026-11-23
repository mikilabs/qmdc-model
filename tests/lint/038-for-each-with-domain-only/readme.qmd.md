# Domain-Only for_each_with [[few_domain: __Workspace]]

## Person Schema [[schema_person: KindSchema]]

- kind: Person

## Meeting Schema [[schema_meeting: KindSchema]]

- kind: Meeting
- required: [participants]

### Field Constraints [[constraints: FieldConstraints]]

- participants: [[#schema_person]]

### Cardinality [[cardinality: Cardinality]]

#### participants [[participants: FieldCardinality]]

- min_count: 1

## Participant Objects Are Meetings [[rule_meeting: LintRule]]

- for_each_with: participants
- assert: kind_of(id) == 'Meeting'
- severity: error
- message: {id} is plumbing, not a domain Meeting

## Meeting [[m1: Meeting]]

- participants: [[#p1]]

## Person [[p1: Person]]

- name: Ann
