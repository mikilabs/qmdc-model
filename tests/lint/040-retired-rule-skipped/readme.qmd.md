# Retired Rule [[retired_rule: __Workspace]]

## Widget [[w1: Widget]]

- name: One

## Old Rule [[rule_old: LintRule]]

- for_each: Widget
- assert: 1 == 0
- severity: error
- message: retired rule must not run
- lifecycle: removed
