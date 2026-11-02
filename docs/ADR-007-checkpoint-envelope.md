# ADR-007: A search envelope with embedded procedure checkpoints

## Status

Accepted and implemented. Resolves the checkpoint-format prerequisite in ADR-006.

## Context

An upstream `Run.checkpoint()` preserves one statistical run, including its RNG
and history. Resuming a graph search additionally needs graph identity, shared
experiments, frontier order, lifecycle states, outstanding reservations and the
policy's state. `Node.state()` alone cannot reconstruct arbitrary experiments.

## Decision

`io/checkpoint.py` owns the versioned JSON format
`sequential-search/checkpoint/1`. `SearchState` contains a graph, two-dimensional
`Budgets`, an ordered frontier, evidence by canonical experiment, ordered
`EdgeState` records, and caller-owned RNG and policy payloads.

The envelope records:

- Root and nodes in insertion order, with one opaque payload per canonical key.
- Edges in node insertion order followed by each node's outgoing-edge order:
  endpoints, rule payload, label, dependency scope, lifecycle and reservations.
- Evidence once per canonical experiment, including sample count and statistic.
- The frontier, both free and reserved budget components, policy and RNG state.

An edge's position identifies it **within this manifest**. Parallel edges remain
distinct. Positions are not persistent identifiers across arbitrary graph edits.
Evidence belongs to a shared experiment; the caller determines which rules
consume it. This module does not infer independence or calibrate tests.

`checkpoint()` receives explicit node/rule encoders. `restore()` receives trusted
node/rule factories and constructs a new graph. Custom statistics also require
an explicit encoder/decoder; ordinary JSON statistics need neither. There are no
pickles, import paths or executable factories in the file. Opaque payloads must
be finite JSON values. Positive infinity in the e-value field has the explicit
representation `"inf"`; NaN and negative infinity are rejected.

Envelope validation runs before restore factories. It rejects unsupported
versions, dangling references, duplicate node/frontier keys, cycles, invalid
lifecycle states, negative/non-finite budgets, and edge reservations that do not
sum to the aggregate reserved amounts. Node factories must reproduce the saved
canonical key and validate their own payloads. JSON copying detaches saved and
restored payloads from live mutable objects.

`WITHDRAW` is persisted without a refund or automatic reopening. `RESUME` is an
external command, not a saved edge state. Restoring a checkpoint changes neither
the evidence nor the budget. Its lifecycle transition belongs to traversal.

### Procedure adapter

`ProcedureNode.checkpoint()` embeds the upstream `Run.checkpoint()` unchanged,
alongside metadata, the last observation, and the last output. Upstream restores
statistical state but not the last output, which the adapter needs to reproduce
`evidence()` and `decision()` immediately. Custom output codecs are explicit;
for SPRT, `dataclasses.asdict` and `SPRTOutput(**payload)` suffice.

`ProcedureNode.restore(factory, payload, decode_output=...)` checks procedure
identity through `Run.restore()` and starts its paused run. Terminal runs stay
terminal. A never-initialized node remains lazy. The default canonical key is
now the node name, rather than `name@t`: observation count must not change an
experiment's identity. Callers with different experiments sharing a display
name must supply distinct explicit keys.

### Example

The caller supplies codecs for its known node and rule types. For a graph of
`ProcedureNode` experiments using one SPRT factory and threshold rules:

```python
import json
from dataclasses import asdict

from sequential_analysis.procedures.sprt import SPRTOutput
from sequential_search.core.edge import threshold_rule
from sequential_search.io.checkpoint import checkpoint, restore
from sequential_search.stats.procedure import ProcedureNode

# state is a SearchState; make_sprt is the caller's trusted procedure factory.
payload = checkpoint(
    state,
    encode_node=lambda node: node.checkpoint(encode_output=asdict),
    encode_rule=lambda rule: {"upper": rule.upper, "lower": rule.lower},
    encode_stat=lambda out: None if out is None else asdict(out),
)
wire = json.dumps(payload, allow_nan=False)
resumed = restore(
    json.loads(wire),
    decode_node=lambda key, data: ProcedureNode.restore(
        make_sprt, data, decode_output=lambda out: SPRTOutput(**out)),
    decode_rule=lambda data: threshold_rule(**data),
    decode_stat=lambda out: None if out is None else SPRTOutput(**out),
)
```

Applications with heterogeneous nodes choose their own factory dispatch. Policy
and RNG owners restore their own JSON representations (for example, Python's
`random.Random.setstate` requires tuples where JSON stores arrays).

## Validation and limits

Tests exercise a diamond DAG, parallel edges, ordered frontier, withdrawn edges,
budgets, JSON isolation, invalid manifests and a core-only interpreter without
upstream. Graph checkpoints at zero, intermediate and terminal SPRT steps
continue identically to a standalone run, including its history digest. A seeded
particle filter also resumes with identical output, state and RNG.

This closes the serialization prerequisite, not the mathematical questions in
ADR-006. It does not implement traversal, a cost-to-go criterion or an
alpha-spending plan. In particular, preserving reservations does not prove
FWER/FDR control under repeated refund and re-reserve. Persistence of an external
tool's state also does not ensure replayability of that external service.

Next: implement traversal against this explicit state contract, then connect
error-budget accounting and validate its statistical assumptions.
