# Metamodel [[_metamodel: __Namespace]]

- description: workspace-wide schema layer

## Thing [[schema_thing: KindSchema]]

- kind: Thing
- required: [title]
- optional: [severity]

## Titled Things Need Severity [[rule_root: LintRule]]

- for_each_with: title
- assert: has('severity')
- severity: error
- message: thing {id} has no severity
