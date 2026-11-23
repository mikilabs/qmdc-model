# for_each_with Field Typo [[few_typo: __Workspace]]

## Widget Schema [[schema_widget: KindSchema]]

- kind: Widget
- required: [marker, name]

## Widget [[w1: Widget]]

- marker: yes
- name: One

## Typo Rule [[rule_typo: LintRule]]

- for_each_with: marker
- assert: has('nmae')
- severity: error
- message: typo must be configuration error
