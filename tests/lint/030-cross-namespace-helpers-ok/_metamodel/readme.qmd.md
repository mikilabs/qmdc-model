# Metamodel [[_metamodel: __Namespace]]

## Pipeline Schema [[schema_pipeline: KindSchema]]

- kind: Pipeline
- required: [name]

## Pipeline Version Schema [[schema_pipeline_version: KindSchema]]

- kind: PipelineVersion
- required: [pipeline]

### Field Constraints [[constraints: FieldConstraints]]

- pipeline: [[#schema_pipeline]]

## Every Pipeline Has A Version [[rule_pipeline_version: LintRule]]

- for_each: Pipeline
- assert: len(incoming(kind='PipelineVersion', via='pipeline')) >= 1
- severity: error
- message: pipeline {id} has no version

## Version References Exist [[rule_version_refs: LintRule]]

- for_each: PipelineVersion
- assert: all(exists(r) and kind_of(r) == 'Pipeline' for r in refs('pipeline'))
- severity: error
- message: pipeline version {id} has a bad pipeline reference
