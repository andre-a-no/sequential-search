# sequential-search: purpose, choices and limits

[English](overview.md) · [Русский](overview.ru.md)

**sequential-search provides mathematical search abstractions and reference
algorithms.** It studies how to reach a goal from available facts or accumulated
observations, with explicit decisions, provenance and resource limits.

Repository: [andre-a-no/sequential-search](https://github.com/andre-a-no/sequential-search).
The Python distribution is named `sequential-search-core`; the import is
`sequential_search`. This checkout requires Python 3.11 or later. It contains
development APIs that must not be assumed to exist in a published release.

## If you do not write code

Imagine that you know two facts and want to establish a third. A rule might
require both facts; several different rules might reach the same conclusion.
Forward search asks what follows from what you know. Backward search asks what
would be sufficient to establish your goal. Bidirectional search joins those
two approaches and checks the connection.

The library supplies algorithms, not an installed end-user application. A
developer supplies the facts, rules, costs and checks appropriate to the task.
No model subscription or API key is needed for its finite reasoning examples.

## Which part should I choose?

| Need | Entry point | Output and limitations |
|---|---|---|
| Derive a goal from a finite positive rule system | `sequential_search.reasoning` | Checked proof, conditional missing premises, exhaustion or resource limit |
| Represent experiments and stopping rules on a graph | `core.node`, `core.edge`, `core.graph` | Experiment contracts, graph identity and edge decisions; not a complete generic executor |
| Adapt an existing statistical procedure | `stats.procedure.ProcedureNode` | Evidence/decisions using sequential-analysis through the optional `full` extra |
| Preserve graph-search state | `io.checkpoint` | Versioned JSON envelope with explicit application codecs; durable storage belongs to applications |
| Run tools or an LLM agent | [sequentialist-agentic](https://github.com/andre-a-no/sequentialist-agentic) | Application integration; it is a separate package |
| Model participants with different goals and coupled actions | [sequential-games](https://github.com/andre-a-no/sequential-games) | Separate mathematical/cybernetic interaction layer |
| Perform a statistical test on one stream | [sequential-analysis](https://github.com/andre-a-no/sequential-analysis) | Statistical procedure rather than a reasoning/search workflow |

## Inputs and results

The finite reasoning API takes a `Problem`: known facts, a goal, a finite tuple
of `Rule` objects and a context identifier. A rule has conjunctive premises;
alternative rules are different ways to reach a conclusion. `solve_forward`,
`solve_backward` and `solve_bidirectional` return a `Result` containing a status,
proof where available, missing premises and resource counters.

`verify_proof` checks rule identities, context, ordering and all required
premises. Conditional proofs need explicit acceptance of their assumptions.
An exhausted finite rule system and a resource-limited search are different
outcomes. Search-work cost and the cost of the returned proof are also distinct.

See the [reasoning contract and executable example](ADR-008-reasoning-search.md)
and [reasoning tests](../tests/test_reasoning.py). For graph persistence, see
the [checkpoint contract](ADR-007-checkpoint-envelope.md) and
[checkpoint tests](../tests/test_checkpoint.py).

## What is implemented, and what is planned?

Implemented in the current development checkout: experiment/edge/budget
contracts, a statistical procedure adapter, the single-edge SPRT anchor, graph
checkpoint serialization, and finite positive propositional reasoning.

Not supplied by those features: a general olympiad solver, arbitrary
predicate-logic inference, a cheapest-proof guarantee, a production search
service, a general resumable experiment traversal, or a proved global
alpha-refund scheme. The graph checkpoint envelope does not by itself persist
an in-flight external service or the finite reasoning algorithm's frontier.

Earlier ADRs discuss many possible applications and previously excluded a
separate games package. They record design history; their proposals are not a
list of implemented APIs. New interaction requirements distinguish
`sequential-games` from search, while applications remain in `sequentialist-*`.

## Frequently asked questions

### Does a checked proof mean the answer is true in the real world?

It establishes derivability within the caller's supplied rules and facts. The
caller must justify those rules, observations and assumptions for the subject.
It is not an automatic clinical, mathematical-domain or engineering validator.

### Does every search result have a statistical error guarantee?

No. Reasoning verification and statistical inference are distinct. A statistical
guard needs its own null/model, calibration and dependence assumptions. An
e-value is not the probability that a branch will succeed. Preserving budget
totals does not establish whole-search FWER/FDR control.

### Is this Dijkstra, A*, a language model, or a framework for agents?

The current reference algorithms work on explicit finite implications and
experiment contracts. They do not claim to replace every shortest-path or
agent framework. Generating an unknown graph and verifying its states can cost
more than traversing its already known edges.

### How do I try the development API?

Clone this repository, create a virtual environment and install the checkout
with `python -m pip install -e '.[dev,full]'`. The `full` extra adds
sequential-analysis; finite reasoning itself uses the standard library.
Follow [AGENTS.md](../AGENTS.md) for tests and the README for repository status.
When using a release, check its tag/source before relying on the newer APIs.

### Can an AI assistant read this documentation?

The repository provides ordinary Markdown and a curated [llms.txt](../llms.txt)
index. A user can give those sources to a browsing or coding assistant, including
Codex, Claude, Qwen, Gemini, Grok or Perplexity where their tools support access.
These files do not guarantee automatic ingestion, indexing, recommendations or
search ranking. Coding guidance is in [AGENTS.md](../AGENTS.md); it is not a
claim about any assistant's automatic file-discovery behavior.

## Authoritative starting points

- [README and status](../README.md)
- [Finite reasoning source](../src/sequential_search/reasoning.py)
- [Experiment contracts](../src/sequential_search/core/node.py)
- [Statistical adapter](../src/sequential_search/stats/procedure.py)
- [Checkpoint source](../src/sequential_search/io/checkpoint.py)
- [Tests](../tests/)

State the selected revision when reporting behavior. Local checks do not imply
that these changes have been published or deployed.
