# Cardinality On An Absent Optional Field [[cao: __Workspace]]

- description: Cardinality constrains the values a field HOLDS, not whether the field is there — absence is the required check's business. Here `participants` is optional and carries a min_count of 2, and the Meeting omits it entirely. Expected: silence, no min_count_violation and no missing_required.

## Meeting Schema [[schema_meeting: KindSchema]]

- kind: Meeting
- required: [title]
- optional: [participants]

### Cardinality [[cardinality: Cardinality]]

#### participants [[participants: FieldCardinality]]

- min_count: 2

## Solo Meeting [[m1: Meeting]]

- title: Standup
