# ADR-008: the dependency graph across the ecosystem

Date: 2026-11-01
Status: accepted (refines ADR-003 layering, ADR-007 item 3)

## Context

Three names have been used for three different things without a stable rule:
"kernel", "core", "wrapper". The owner's decision (ADR-007): this project is
`sequential-search`, the `-core` suffix is dropped because *the* core lives
elsewhere. That leaves the question of who depends on whom and why — including
two packages that do not exist yet (`sequentialist-core`, `sequentialist-visuals`)
and the applied software built on top of them.

## Decision

### The graph

```
                        sequential-analysis          [upstream, third party]
                        procedures, RNG semantics, checkpoints
                                    |
                          required  |  optional ([full] extra)
                                    v
   SEQUENTIAL-SEARCH  <----------- (this repo)       [math layer]
   graph/ stats/ policy/ io/ interpreters/            no domain vocabulary
        \                    /
         \                  /   both depend on it, never on each other
          v                v
   sequentialist-core   sequentialist-visuals        [interpretation layer]
   vocab, data          plots over traversal state,
   connectors, DSL      replay, budget dashboards
          \                /
           \              /   application packages depend on BOTH
            v            v
   applied software (domain-specific repos)          [application layer]
```

Edges, stated as rules:

| # | Rule | Enforcement |
|---|---|---|
| D1 | `sequential-analysis` may be imported by `sequential-search` **only** inside `stats/procedure.py`. Contracts in `graph/` must stay upstream-free. | grep gate in CI; degenerate anchor has 16 tests that pass with upstream absent |
| D2 | `sequential-search` depends on nothing else. It never imports any `sequentialist-*` or application package. | hard, by review |
| D3 | `sequentialist-core` depends on `sequential-search`; it does **not** depend on `sequential-visuals`. | declared in its pyproject |
| D4 | `sequentialist-visuals` depends on `sequential-search` (for types/state) and optionally on `sequentialist-core`; it must work on serialized traversal state alone. | its public API takes dicts/checkpoints, not live objects |
| D5 | `sequentialist-core` and `sequentialist-visuals` are siblings: neither imports the other's internals. Anything they share lives in `sequential-search`. | the only legal place for shared code is upstream |
| D6 | An application package depends on both interpretation packages explicitly; it must not reach into `sequential_search.*` unless it declares itself math-level. | import-linter contract per repo |
| D7 | Version coupling: `sequential-search` pins upstream as `>=0.4,<0.5` (checkpoint format is part of the contract). Interpretation layers pin `sequential-search` the same way. | pyproject |

### Why upstream is an extra, not a dependency (D1)

The contracts and the degenerate anchor are testable without `sequential-analysis`
installed. This keeps the math layer installable in environments where the
upstream is unavailable (offline CI, minimal containers) and makes the adapter
boundary explicit rather than ambient. Consequence: `pip install sequential-search`
gives ontology + budgets + policies; `pip install sequential-search[full]` adds
procedure adapters.

### Vocabulary (replaces "kernel/core/wrapper")

- **math layer** = `sequential-search`. Contains algorithms and guarantees.
- **interpretation layer** = `sequentialist-core`, `sequentialist-visuals`.
  Turns nodes/edges into domain objects and back again.
- **application layer** = domain repos. Owns data sources, UI, business rules.

The prefix `sequentialist-` marks the interpretation family; the absence of a
suffix on `sequential-search` marks the math layer (ADR-007).

### Where each open item lands

| Item from LIT-001 / ADR-004..006 | Layer | Package |
|---|---|---|
| adaptive-multiplicity error control | math | `sequential-search/stats/error_budget.py` |
| coupled observations across nodes (gap A) | math | `sequential-search/graph/node.py` (`dependency_scope`) |
| comparing two sampling locations (gap B) | math | new `stats/comparison.py` — needs literature check first |
| perpetual traversal + switching cost (gap C/D) | math | `sequential-search/graph/traversal.py` |
| channel/beam/slice/vocab vocabulary | interpretation | `sequentialist-core` |
| traversal replay, budget dashboards | interpretation | `sequentialist-visuals` |
| tomography pipelines, agent runtimes | application | separate repos |

## Consequences

- Nothing new to implement right now in this repo: the graph above is a set of
  prohibitions, and today we already violate none of them.
- Before `sequentialist-core` is created, its pyproject must be reviewed against
  D3–D7; otherwise the sibling boundary (D5) gets blurred by convenience imports.
- `interpreters/` stays in the math layer as spec-by-example (ADR-003); if any
  file there starts importing domain vocabulary, it moves down to
  `sequentialist-core` rather than growing here.
