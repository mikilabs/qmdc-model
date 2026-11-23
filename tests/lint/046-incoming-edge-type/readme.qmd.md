# Incoming Edge Type [[incoming_role: __Workspace]]

## Module Schema [[schema_module: KindSchema]]

- kind: Module
- required: [name]

## Narrative Schema [[schema_doc: KindSchema]]

- kind: NarrativeDoc
- optional: [about, overview]

## Module Is Documented [[rule_documented: LintRule]]

- for_each: Module
- assert: len(incoming(kind='NarrativeDoc', via='about')) > 0
- severity: error
- message: module {id} has no incoming about edge

## API [[api: Module]]

- name: API

## Architecture [[doc: NarrativeDoc]]

### Overview [[overview: text]]

- about: [[#api]]

The API accepts requests.
