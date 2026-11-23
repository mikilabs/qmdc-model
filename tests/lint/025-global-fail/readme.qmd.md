# Global Fail [[g_bad: __Workspace]]

- description: A global LintRule (graph-wide invariant) that fails → rule_failed with empty object

## Must Have Index [[rule_index: LintRule]]

- global: true
- assert: exists('index')
- severity: error
- message: the workspace must declare an index object

## Catalog [[catalog: Index]]

- title: Catalog
