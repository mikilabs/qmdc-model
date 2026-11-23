# Pairwise Overlap [[pair_overlap: __Workspace]]

## Table Schema [[schema_table: KindSchema]]

- kind: Table

## Booking Schema [[schema_booking: KindSchema]]

- kind: Booking
- required: [tables]

## No Shared Table [[rule_no_overlap: LintRule]]

- global: true
- assert: all(id_of(a) == id_of(b) or not overlaps(refs_of(a, 'tables'), refs_of(b, 'tables')) for a in all_of('Booking') for b in all_of('Booking'))
- severity: error
- message: two bookings share a table

## Table [[t1: Table]]

- seats: 4

## First [[b1: Booking]]

- tables: [[#t1]]

## Second [[b2: Booking]]

- tables: [[#t1]]
