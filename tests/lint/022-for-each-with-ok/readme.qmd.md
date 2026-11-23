# For-Each-With OK [[few_ok: __Workspace]]

- description: A for_each_with LintRule scoping objects that carry a field; assert holds → clean

## Overlay Needs Reason [[rule_overlay: LintRule]]

- for_each_with: overlay_of
- assert: has('reason')
- severity: warning
- message: overlay {id} must state a reason

## Patch Overlay [[ov1: Overlay]]

- overlay_of: [[#base]]
- reason: tighten capacity for safety

## Base Config [[base: Config]]

- capacity: 20
