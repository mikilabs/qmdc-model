# Unsafe Assert [[unsafe_assert: __Workspace]]

## Escape [[rule_escape: LintRule]]

- global: true
- assert: len([c for c in ().__class__.__mro__[1].__subclasses__() if c.__name__ == 'BuiltinImporter']) == 0
- severity: error
- message: arbitrary Python object traversal must never execute
