# Multiple Selectors [[multi_selector: __Workspace]]

## Session [[s1: Session]]

- title: Test

## Conflicting Rule [[rule_conflict: LintRule]]

- for_each: Session
- for_each_with: title
- assert: 1 == 1
- severity: error
- message: exactly one selector is required
