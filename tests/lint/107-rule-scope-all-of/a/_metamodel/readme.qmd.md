# A Metamodel [[a._metamodel: __Namespace]]

- description: extension A schema layer

## A Owns Exactly One Thing [[rule_a_one_thing: LintRule]]

- global: true
- assert: len(all_of('Thing')) == 1
- severity: error
- message: namespace a must hold exactly one Thing
