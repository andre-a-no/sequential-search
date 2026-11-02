# ADR-008: Finite implication search as a reference mathematical layer

## Status

Implemented as a bounded P0 reference in `sequential_search.reasoning`.

## Context and scope

The existing `Node` contract describes an experiment supplying observations.
Forward or backward derivation has different semantics: known facts imply new
facts, and a desired conclusion may require several sufficient premises.
Replacing `Node.step()` with proof search would change its contract.

The new module therefore provides pure algorithms over finite positive
propositional implications. Facts are non-empty string identifiers. Their
subject meaning and the validity of implication rules belong to the caller.
This is a reference composition for checking the architecture, not a general
olympiad solver, predicate-logic prover, or operational search service.

## Public contract

- `Rule(name, premises, conclusion, cost=1.0)` represents conjunctive premises.
  Multiple rules deriving a conclusion are alternative methods.
- `Problem(facts, goal, rules, context="default")` declares the entire finite
  system and a caller-owned context/version identifier. Rule names are unique.
- `Proof(context, goal, steps=(), assumptions=frozenset())` records a
  topologically ordered sequence of rule names and explicit missing premises.
- `Result` reports `status`, `proof`, `missing`, `expansions`, cumulative search
  `cost`, and the separate `proof_cost` of the returned derivation.
- `verify_proof(problem, proof, allow_assumptions=False)` checks context, goal,
  rule identities, all required premises and the connection to the goal.

The verification establishes entailment within the explicit implication system.
It does not establish that domain rules correctly describe geometry, medicine
or physical equipment. Context identity is supplied by the application; the
algorithm does not infer compatibility from proposition text.

Unused valid derivation steps are permitted, but an assumption must actually
support the goal. Duplicate steps, assumptions equal to the goal, assumptions
already known as facts and assumptions subsequently derived in the proof are
rejected. Conditional proofs require explicit `allow_assumptions=True`.

## Algorithms

`solve_forward` derives the positive closure in declared rule order. Each new
fact has one recorded producer, shared between paths. A producer is applied
only after all its premises are available.

`solve_backward` performs breadth-first exploration of obligation sets. Selecting
a producer replaces one obligation with all its premises. Alternative producers
branch the search. Each candidate chooses at most one producer per conclusion;
the finite candidate space is deduplicated. Candidate proofs are extracted
without recursion and rejected if their support is cyclic. An unproduced leaf
may become an explicit missing premise, but an intermediate atom is not assumed
just to break a cycle. Merely assuming the original goal is not a result.

`solve_bidirectional` computes a bounded forward prefix, then uses its derived
facts as backward cut points. It replaces those cut points with their forward
provenance, topologically orders the combined derivation, and checks it against
the **original** facts and context. `forward_steps=1` is the default split;
callers may choose another non-negative bound. This reference is not a balanced,
cost-optimal bidirectional algorithm.

All three methods return a validated unconditional proof as soon as one is
found. No method claims the cheapest proof. In a finite rule system with no
binding limits, they find an unconditional proof whenever positive entailment
holds. Without a proof, forward saturation reports `exhausted`; backward search
can report a checked `conditional` proof with missing source premises. A cycle
without grounded support is exhausted, not promoted to a conditional proof.

## Resource and outcome semantics

`max_expansions` defaults to 10,000. `max_cost` defaults to positive infinity.
They bound the work of the chosen algorithm, not the domain's physical resource
budget and not statistical alpha.

- A forward expansion is a rule applicability check. Failed checks consume an
  expansion; a successful new derivation additionally consumes its rule cost.
- A backward expansion explores a producer choice or records an unproduced
  leaf. Rule cost is charged for every explored producer, including branches
  later discarded. Recording an unproduced leaf has zero rule cost.
- The bidirectional phases share the same counters and budget.
- `proof_cost` sums the rules actually used by the returned proof. It may be
  smaller than cumulative search `cost`.

An attempted expansion that cannot fit a limit marks an incomplete search.
Other affordable alternatives may still produce a valid proof. If none does,
the status is `resource_limit`, not an assertion of nonexistence. A best checked
conditional candidate may accompany that status; it is not a successful result.
With no producer for the goal, the result is exhausted with the goal listed in
`missing`, rather than a tautological proof that assumes the goal itself.

## Example

```python
from sequential_search.reasoning import Problem, Rule, solve_bidirectional, verify_proof

problem = Problem(
    facts=frozenset({"a", "b"}),
    goal="goal",
    rules=(
        Rule("lemma", frozenset({"a"}), "intermediate"),
        Rule("finish", frozenset({"intermediate", "b"}), "goal"),
    ),
    context="example/v1",
)
result = solve_bidirectional(problem)
assert result.status == "proved"
assert result.proof is not None
assert verify_proof(problem, result.proof)
```

## Validation and deferred work

Tests cover AND/OR structure, missing premises, alternative proofs, cycles,
incompatible contexts, limits, combined provenance and a 1,200-step chain without
Python recursion. Fifty small generated systems are checked against an
independent exhaustive truth-table entailment oracle.

Existing experiment APIs and checkpoint formats are unchanged. This module has
no upstream statistical dependency. Linking derivation search to experiments,
resumable algorithm-state envelopes, heuristic selection, dynamic rule discovery,
predicate variables and subject-specific inference/validators are separate work.
No statistical or whole-search error-control guarantee is implied by proof
verification.
