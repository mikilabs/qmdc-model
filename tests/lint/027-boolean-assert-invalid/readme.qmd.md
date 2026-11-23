# Boolean Assert [[bool_assert: __Workspace]]

## Session [[s1: Session]]

- title: Test

## Boolean Rule [[rule_true: LintRule]]

- for_each: Session
- assert: true
- severity: error
- message: must not leak a Python eval traceback
