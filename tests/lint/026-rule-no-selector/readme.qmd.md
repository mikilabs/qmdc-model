# Rule No Selector [[rns: __Workspace]]

- description: A LintRule with an assert but no scope selector (for_each / for_each_with / global) → rule_no_selector

## Dangling Rule [[rule_dangling: LintRule]]

- assert: has('title')
- severity: error
- message: this rule declares no scope and cannot run

## Some Session [[s1: Session]]

- title: A Session
