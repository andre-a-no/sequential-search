# sequential-search

**Sequential statistical decision-making during graph traversal** (math layer).
It inherits the problem setting of
[`sequential-analysis`](https://pypi.org/project/sequential-analysis/) but moves
it from a flat stream of observations onto a graph: every traversal is a stream
of experiments, and every edge is a statistical decision.

The name says what this is *not*: it is not the interpretation layer built on
top of it (`sequentialist-core`, `sequentialist-visuals`), and it is not a
"core" — the core procedures live upstream in `sequential-analysis`. What
distinguishes it is that decisions are taken **sequentially**, along a
traversal; a classical binary test appears only as a degenerate case.

A classical binary test (SPRT and friends) is the degenerate case of a graph
`root → leaf` with a single edge.

## Ontology (see `docs/ADR-001-graph-nodes-as-experiments.md`)

| Entity | What it is | What it is *not* |
|---|---|---|
| **Node** | an experiment: `step() -> Observation`, `state() -> EvidenceState`, `cost` | data, a hypothesis, a score |
| **Edge** | a stopping rule: accumulated evidence → decision `accept / reject / pending` | a boolean predicate (that is only its degenerate case) |
| **Traversal** | a traversal policy + a global error budget (α-risk *and* resource) | a `for node in graph` loop |

## Interpretations the math layer must be able to express

1. Filter cascades (pipeline, group-sequential).
2. Adaptive conditioning trees (adaptive sampling designs).
3. Streams of hypotheses with online FDR (LORD/LTSI, graph-based FDR).
4. HMM state maps / change-point detection (CUSUM, BOCPD as traversal
   trajectories).
5. **Coarse-to-fine hierarchical refinement**: tomographic depth search
   (average a block of slices → SPRT decision on whether to descend to thinner
   slices), image pyramids, and any search over a resolution tree where
   **observation cost differs per level**.
6. **Statistical agent policies**: instead of heuristics like "run N steps then
   score", an anytime-valid criterion at every action continuation
   (perpetual traversal).
7. **Inference tree (statistical branch-and-bound)**: solving a task from the
   givens toward the answer; a node is an intermediate state, an edge is
   "should this branch be continued?". "I am overcomplicating this, I should
   have done something else" = a CUSUM change-point detector on progress
   increments plus a violated expected-cost-to-success inequality relative to
   sibling branches. See `docs/ADR-002-traversal-as-conjecture-lifecycle.md`.
8. **Tracking a moving object** (the object itself travels over its own graph;
   we decide whether to reposition, and we pay for moving). An opponent with
   their own strategy is a degenerate case of an adaptive environment — no
   separate game library is created. ⚠️ This case is **not yet expressible on
   the current math layer**: it exposes three gaps (observations coupled through the
   environment, comparing two sampling locations, perpetual + switching cost).
   See `docs/ADR-004-environment-as-adversary.md`.
9. **Cooperative search for a shared state (sequential matching)**: transmitter
   and receiver independently turn their knobs looking for the best channel,
   with a shared payoff. Cooperation requires no game theory, but it does
   require a **common e-budget** across both sides. "Given the circumstances, I
   should stand up" is the `WITHDRAW` outcome, distinct from `REJECT`: stopping
   because continuing has lost its value, not because the hypothesis was
   refuted, with a refund of unspent α. ⚠️ Not expressible until gap B is
   closed. See `docs/ADR-005-cooperative-matching-and-withdrawal.md`.
10. **Resuming after standing up**: `WITHDRAW` needs the inverse transition
    `RESUME`, otherwise policies will fear closing a branch and will
    under-spend the budget. Contract requirement: `RESUME` must restore the
    accumulated evidence rather than restart the search (otherwise the α-reserve
    is spent twice). A known partner strategy vs. an unknown one are different
    problem settings: the first yields an exact guarantee (conditional power),
    the second only an anytime-valid upper bound; both are expressed through
    node parameters, and adversarial mode is kept **out of scope for the math layer**.
    See `docs/ADR-006-resumable-search-and-known-partner.md`.

Applied interpretations do **not** live here: they belong to the interpretation
layer (`sequentialist-core`, `sequentialist-visuals`) and to the application
repos built on top of it. See the dependency graph below.

## Dependency graph (see `docs/ADR-008-dependency-graph.md`)

```
                    sequential-analysis          [upstream: procedures, RNG, checkpoints]
                                 |
                       required   |   optional ([full] extra)
                                 v
        SEQUENTIAL-SEARCH  (this repo)            [math layer: no domain vocabulary]
        graph/ stats/ policy/ io/ interpreters/
              \                      /
               \                    /   siblings: depend on the math layer, never on each other
                v                  v
     sequentialist-core    sequentialist-visuals  [interpretation layer]
     vocabulary, data      plots over traversal state,
     connectors, DSL       replay, budget dashboards
                \                  /
                 \                /   application repos depend on BOTH
                  v              v
             applied software                   [application layer]
```

Hard rules: upstream is imported **only** inside `stats/procedure.py` (D1); this
package imports nothing from `sequentialist-*` or any application package (D2);
the two interpretation packages are siblings and anything they would share moves
up here (D5). Vocabulary: *math layer* / *interpretation layer* / *application
layer* — the words "kernel" and "core" are retired for this repo (ADR-007), since
the core procedures live upstream.

## Package layout

```
src/sequential_search/
├── graph/           # graph ontology (was: core/, renamed by ADR-007)
│   ├── node.py      # Node protocol, Observation, canonical_key
│   ├── edge.py      # Edge, StoppingRule, Decision (+WITHDRAW/RESUME)
│   ├── graph.py     # SearchGraph: DAG with node merging, dynamic expansion
│   └── traversal.py # Traversal: finite / perpetual / resumable, checkpoints
├── stats/           # mathematics (adapters over sequential-analysis, [full] only)
│   ├── procedure.py # Procedure adapter (SPRT, mSPRT, group-sequential…)
│   ├── evidence.py  # e-values, likelihood ratios, evidence accumulation
│   ├── error_budget.py  # offline/online FWER/FDR control, alpha-spending
│   └── stopping.py  # StoppingRule, anytime-valid boundaries
├── policy/          # choosing the next node
│   ├── base.py
│   ├── exhaustive.py    # full DFS/BFS — the basic working case
│   ├── bandit.py        # budget allocation (info per cost, VOI lower bound)
│   └── budget.py        # resource-aware: node costs ∈ budget
├── interpreters/    # reference "graph ↔ task" mappings (minimal)
│   ├── hypotheses.py
│   ├── sampling.py
│   ├── pipeline.py
│   ├── hierarchy.py     # tomography/pyramids: coarse-to-fine
│   ├── inference.py     # inference tree: proof search / stat. branch-and-bound
│   ├── tracking.py      # case 8: tracking; ✗ not expressible today (ADR-004)
│   └── matching.py      # case 9: cooperative channel search; ✗ until gaps B/D (ADR-005)
└── io/              # serialization, checkpoints (format compatible with sequential-analysis)
```

## Layer invariants

1. **Global guarantee**: family-wise error ≤ α across the whole traversal, even
   when the policy adapts the order of tests (e-value calibration on edges).
2. **Degenerate anchor**: a single-edge graph ≡ standalone SPRT from
   `sequential-analysis` (the test is fixed before traversal is implemented).
3. **Checkpointability**: the state of an entire traversal is serializable and
   reproducible (RNG semantics inherited).
4. **Cost-awareness**: `Node.cost` participates in the policy; no
   next-node-selection strategy may violate the α guarantee.
5. **No double counting**: the graph is a DAG; re-entering a canonically
   identical node does not create a new experiment and does not duplicate the
   accumulated evidence (otherwise multiplicity of testing is hidden and
   invariant 1 breaks).
6. **Separation of evidence and cost** (E4): a stopping rule cannot produce
   `WITHDRAW`/`RESUME` — those follow from the cost of continuation at the
   traversal level, not from the strength of the evidence. Otherwise an
   "exhausted test" would be indistinguishable from a "refuted" one.
7. **Budget conservativity** (B1/B2): α is reserved against an edge and only
   spent on ACCEPT/REJECT; a refund never exceeds the reservation. Without
   this, `WITHDRAW` would print α and invariant 1 would lose its meaning.

## Status

The project is in the design stage. Accepted decisions are documented as ADRs in
`docs/`.

**Implemented**: layer 1 (contracts `graph/node.py`, `graph/edge.py`,
`graph/graph.py`, `policy/base.py`) + the `stats/procedure.py` adapter + the
degenerate anchor (20 tests, green; 16 of them run without the upstream package
installed — the upstream dependency is optional by design, ADR-003).

**Degenerate-anchor specification** is fixed by the code in
`tests/test_degenerate_anchor.py`; no separate markdown file was created for it
(an earlier summary mentioned it by mistake) — treat the test as the source of
truth.

**Order of the next steps** (changed by ADR-006): `io/checkpoint.py` →
`graph/traversal.py` → `stats/error_budget.py` → `interpreters/hierarchy.py`.
Checkpoints come before traversal because `RESUME` requires preserving the
accumulated evidence, and without it `WITHDRAW` cannot be made reversible
without losing the guarantee.

**Blocking open question**: the checkpoint envelope format and its compatibility
with `sequential-analysis` (`checkpoint()/restore()`). Traversal is not written
until this is settled.

## Installation (once published)

```bash
pip install sequential-search        # contracts only, no upstream dependency
pip install sequential-search[full]  # + procedure adapters over sequential-analysis
```

PyPI availability of the plain name `sequential-search` is checked before the
first release (ADR-007); nothing is pre-reserved.

## License

AGPL-3.0 (compatible with the upstream dual licensing).
