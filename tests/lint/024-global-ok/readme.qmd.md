# Global OK [[g_ok: __Workspace]]

- description: A global LintRule (graph-wide invariant) that holds → clean

## Must Have Index [[rule_index: LintRule]]

- global: true
- assert: exists('index')
- severity: error
- message: the workspace must declare an index object

## Index [[index: Index]]

- title: Catalog
