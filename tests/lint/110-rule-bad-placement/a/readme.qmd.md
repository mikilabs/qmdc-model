# A [[a: __Namespace]]

- description: extension A, keeping its schema, its rule and its data in one namespace

## Issue [[schema_issue: KindSchema]]

- kind: a.Issue
- required: [title, severity]

## Payment Failure [[issue_a: a.Issue]]

- title: payment failure
- severity: error

## Titled Things Need Severity [[rule_a: LintRule]]

- for_each_with: title
- assert: has('severity')
- severity: error
- message: rule_a fired on {id}
