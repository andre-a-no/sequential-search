# ADR-007: naming — the package is `sequential-search`, not `-core`

Date: 2026-11-01
Status: accepted (supersedes ADR-003 item 3)

## Context

ADR-003 settled the distribution name as `sequential-search-core` to hedge
against the PyPI name possibly being taken. The owner rejected this: "core is
already elsewhere; this project *is* the layer above it." The distinguishing
property of the package is not that it is a kernel — it is that it is
**sequential**: decisions are taken incrementally along a traversal, and a
classical binary test is recovered only as a degenerate parameterisation.

## Decision

1. Distribution and import name: `sequential-search` / `sequential_search`.
   The `-core` suffix is dropped everywhere (pyproject, README, docs).
2. The module formerly called `core/` is renamed to `graph/`: its content is the
   graph ontology (Node/Edge/SearchGraph), and calling it "core" contradicted
   point 1. `stats/`, `policy/`, `io/`, `interpreters/` keep their names.
3. Layering vocabulary changes from "kernel vs wrapper" to
   **"math layer vs interpretation layer"** (`sequentialist-search`). Both are
   layers over `sequential-analysis`; neither is "the core".
4. PyPI availability of `sequential-search` must be checked before the first
   release; if taken, the fallback is a scoped namespace decided by the owner at
   that moment — do not pre-reserve anything.

## Consequences

- Renaming is a breaking change for any external consumer; there are none yet,
  so it is done now rather than after 0.1.
- Docs (ADRs, LIT) remain in Russian for now; code comments, docstrings, README
  and commit messages are English-only (owner's instruction).
