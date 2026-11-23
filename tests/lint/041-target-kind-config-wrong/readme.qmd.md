# Bad Target-Kind Schema [[bad_target_schema: __Workspace]]

## Thing Schema [[schema_thing: KindSchema]]

- kind: Thing

## Widget Schema [[schema_widget: KindSchema]]

- kind: Widget
- required: [owner]

### Field Constraints [[constraints: FieldConstraints]]

- owner: [[#plain]]

## Plain Thing [[plain: Thing]]

- name: Plain

## Widget [[w1: Widget]]

- owner: [[#plain]]
