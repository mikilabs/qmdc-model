# Object Collection Overlap [[object_overlap: __Workspace]]

## Widget Schema [[schema_widget: KindSchema]]

- kind: Widget

## Rule [[rule_bad_overlap: LintRule]]

- global: true
- assert: overlaps(all_of('Widget'), all_of('Widget'))
- severity: error
- message: object dicts are not member ids

## Widget [[w1: Widget]]

- name: One
