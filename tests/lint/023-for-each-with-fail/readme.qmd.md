# For-Each-With Fail [[few_bad: __Workspace]]

- description: A for_each_with LintRule scoping objects that carry a field; assert fails → rule_failed

## Overlay Schema [[schema_overlay: KindSchema]]

- kind: Overlay
- required: [overlay_of]
- optional: [reason]

## Overlay Needs Reason [[rule_overlay: LintRule]]

- for_each_with: overlay_of
- assert: has('reason')
- severity: warning
- message: overlay {id} must state a reason

## Patch Overlay [[ov1: Overlay]]

- overlay_of: [[#base]]

## Base Config [[base: Config]]

- capacity: 20
