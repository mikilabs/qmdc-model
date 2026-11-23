# AI-DLC Experiments [[aidlc_experiments: __Workspace]]

- description: Metamodel for testing AI-DLC engine versions and overlays against target repos

Domain metamodel for reproducible AI-DLC experiments. The central object is the Run:
one execution of a Task against a Target, using an Engine plus zero or more Overlays,
carried up to a chosen stage. Comparison across engine/overlay combinations is a query
over Runs, not a stored entity.

The metamodel (Kinds, field constraints, cross-object rules) lives in the `_metamodel`
namespace. Vendored base meta-kinds live there too as `*.vendor.qmd.md`. Domain objects
(Runs, Engines, ...) live in the workspace root and other namespaces.
