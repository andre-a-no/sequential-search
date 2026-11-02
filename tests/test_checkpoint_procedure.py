"""The graph envelope resumes the same SPRT as the standalone upstream run."""
from __future__ import annotations

import json
from dataclasses import asdict, replace

import pytest

pytest.importorskip("sequential_analysis", reason="requires the full extra")
from sequential_analysis import Run
from sequential_analysis.procedures import SPRT, Gaussian
from sequential_analysis.procedures.sprt import SPRTOutput

from sequential_search.core.edge import Decision, Edge, threshold_rule
from sequential_search.core.graph import SearchGraph
from sequential_search.io.checkpoint import EdgeState, SearchState, checkpoint, restore
from sequential_search.policy.base import Budgets
from sequential_search.stats.procedure import ProcedureNode, wald_thresholds

DATA = [0.1, 0.9, 1.2, 0.7, 1.5, 1.1, 0.8, 1.9]


def procedure():
    return SPRT(Gaussian(1.0), 0.0, 1.0, alpha=0.05, beta=0.1)


def roundtrip(state):
    data = checkpoint(
        state,
        encode_node=lambda node: node.checkpoint(encode_output=asdict),
        encode_rule=lambda rule: {"upper": rule.upper, "lower": rule.lower},
        encode_stat=lambda output: None if output is None else asdict(output),
    )
    return restore(
        json.loads(json.dumps(data, allow_nan=False)),
        decode_node=lambda key, payload: ProcedureNode.restore(
            procedure, payload, decode_output=lambda output: SPRTOutput(**output)),
        decode_rule=lambda payload: threshold_rule(**payload),
        decode_stat=lambda output: None if output is None else SPRTOutput(**output),
    )


@pytest.mark.parametrize("split", [0, 1, 5, 8])
def test_graph_checkpoint_preserves_withdrawn_evidence_and_standalone_continuation(split):
    graph = SearchGraph()
    graph.add_node(ProcedureNode("root", procedure))
    node = ProcedureNode("trial", procedure, seed=17)
    graph.add_node(node)
    graph.add_edge(Edge("root", "trial", threshold_rule(*wald_thresholds(0.05, 0.1))))
    standalone = Run(procedure(), seed=17)
    standalone.start()
    for x in DATA[:split]:
        standalone.step({"x": x})
        node.feed({"x": x})
    decision = node.decision() if node.is_terminal() else Decision.WITHDRAW
    state = SearchState(graph, Budgets(0.05, 10.0), (), {"trial": node.evidence()},
                        (EdgeState(decision),))
    # Loading multiple times must neither reset evidence nor consume/refund alpha.
    loaded = roundtrip(roundtrip(state))
    restored_node = loaded.graph.node("trial")
    assert loaded.evidence["trial"] == node.evidence() == restored_node.evidence()
    assert loaded.edge_states == state.edge_states
    assert loaded.budgets == state.budgets
    assert restored_node.is_terminal() == node.is_terminal()

    # An explicit caller transition reopens the suspended edge. The persistence
    # layer itself neither makes this decision nor changes its statistical test.
    if not restored_node.is_terminal():
        loaded = replace(loaded, frontier=("trial",), edge_states=(EdgeState(),))
    for x in DATA[split:]:
        event = standalone.step({"x": x})
        evidence = restored_node.feed({"x": x})
        assert evidence.stat == event.output
        assert restored_node.state() == standalone.state
        assert loaded.graph.out_edges("root")[0].decide(evidence) == restored_node.decision()
    assert restored_node.is_terminal()
    assert restored_node.state() == standalone.state
    assert restored_node._ensure_run().history_digest == standalone.history_digest
