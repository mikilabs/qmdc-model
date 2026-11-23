# Rule Field Typo [[field_typo: __Workspace]]

## Loan Schema [[schema_loan: KindSchema]]

- kind: Loan
- required: [status]

## Loan [[loan1: Loan]]

- status: active

## Typo Rule [[rule_typo: LintRule]]

- for_each: Loan
- assert: field('stauts') == 'active'
- severity: error
- message: this is broken configuration, not a violation on every Loan
