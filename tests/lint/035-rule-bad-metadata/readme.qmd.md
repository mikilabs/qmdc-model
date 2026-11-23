# Bad Rule Metadata [[bad_metadata: __Workspace]]

## Thing [[t1: Thing]]

- name: x

## Bad Severity [[rule_severity: LintRule]]

- for_each: Thing
- assert: 1 == 1
- severity: critical
- message: severity must be closed

## Bad Message [[rule_message: LintRule]]

- for_each: Thing
- assert: 1 == 1
- severity: error
- message: 42
