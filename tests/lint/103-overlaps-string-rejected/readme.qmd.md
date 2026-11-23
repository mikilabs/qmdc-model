# Bad Overlap Types [[bad_overlap: __Workspace]]

## Widget Schema [[schema_widget: KindSchema]]

- kind: Widget
- required: [tags, other_tags]

## Rule [[rule_overlap: LintRule]]

- for_each: Widget
- assert: not overlaps(field('tags'), field('other_tags'))
- severity: error
- message: tags must be disjoint

## Widget [[w1: Widget]]

- tags: a, b
- other_tags: c, d
