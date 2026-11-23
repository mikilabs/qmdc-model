# A Metamodel [[a._metamodel: __Namespace]]

- description: extension A schema layer

## Issue [[schema_issue: KindSchema]]

- kind: a.Issue
- required: [title, severity]
- strict: true

## Titled Things Need Severity [[rule_a: LintRule]]

- for_each_with: title
- assert: has('severity')
- severity: error
- message: rule_a fired on {id}
