"""Search snapshots preserve shared experiments, lifecycle and accounting."""
from __future__ import annotations

import copy
import json
import math
import random
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from sequential_search.core.edge import Decision, Edge, EvidenceState, threshold_rule
from sequential_search.core.graph import SearchGraph
from sequential_search.core.node import Observation
from sequential_search.io.checkpoint import (
    CheckpointError,
    EdgeState,
    SearchState,
    checkpoint,
    restore,
)
from sequential_search.policy.base import Budgets


class Counter:
    def __init__(self, key, values=None):
        self.name = key
        self.values = [] if values is None else values

    def canonical_key(self):
        return self.name

    def state(self):
        return self.values

    def step(self):
        self.values.append(len(self.values) + 1)
        return Observation(len(self.values), {"x": self.values[-1]})

    def cost(self):
        return 1.0

    def is_terminal(self):
        return False


def save(state, **kwargs):
    return checkpoint(state, encode_node=lambda node: node.state(),
                      encode_rule=lambda rule: [rule.upper, rule.lower], **kwargs)


def load(data, **kwargs):
    return restore(data, decode_node=lambda key, payload: Counter(key, payload),
                   decode_rule=lambda payload: threshold_rule(*payload), **kwargs)


def diamond():
    graph = SearchGraph()
    for key in ("root", "left", "right", "shared"):
        graph.add_node(Counter(key))
    for source, target in (("root", "left"), ("root", "right"),
                           ("left", "shared"), ("right", "shared")):
        graph.add_edge(Edge(source, target, threshold_rule(20.0, 0.1),
                            label=f"{source}:{target}", dependency_scope="experiment"))
    graph.node("shared").step()
    return SearchState(
        graph, Budgets(0.03, 90.0, 0.02, 10.0), ("right", "shared", "left"),
        {"shared": EvidenceState(2.0, {"log_lr": math.log(2.0)}, 1)},
        (EdgeState(Decision.ACCEPT), EdgeState(),
         EdgeState(Decision.WITHDRAW), EdgeState(Decision.PENDING, 0.02, 10.0)),
        rng_state=random.Random(13).getstate(), policy_state={"visited": ["root", "shared"]},
    )


def test_json_roundtrip_preserves_dag_frontier_lifecycle_and_budgets():
    state = diamond()
    data = json.loads(json.dumps(save(state), allow_nan=False))
    loaded = load(data)

    assert list(loaded.graph.keys()) == list(state.graph.keys())
    assert loaded.graph.root == "root"
    assert len(loaded.graph) == 4
    assert loaded.graph.out_edges("left")[0].target == loaded.graph.out_edges("right")[0].target
    assert loaded.graph.node("shared").state() == [1]
    assert loaded.frontier == ("right", "shared", "left")
    assert loaded.edge_states == state.edge_states  # WITHDRAW stays withdrawn
    assert loaded.budgets == state.budgets  # no automatic refunds on loading
    assert loaded.evidence == state.evidence
    assert loaded.policy_state == state.policy_state
    for key in tuple(state.graph.keys()):
        for before, after in zip(state.graph.out_edges(key), loaded.graph.out_edges(key)):
            assert (after.source, after.target, after.label, after.dependency_scope) == (
                before.source, before.target, before.label, before.dependency_scope)
            assert after.decide(loaded.evidence["shared"]) == before.decide(state.evidence["shared"])

    # RNG state is caller-owned: random.Random needs tuples rather than arrays.
    version, words, gauss = loaded.rng_state
    resumed_rng = random.Random()
    resumed_rng.setstate((version, tuple(words), gauss))
    assert resumed_rng.random() == random.Random(13).random()


def test_snapshot_and_loaded_nodes_do_not_alias_live_or_serialized_state():
    state = diamond()
    saved = save(state)
    loaded = load(saved)
    state.graph.node("shared").step()
    state.evidence["shared"].stat["log_lr"] = -10
    state.policy_state["visited"].append("left")
    saved["nodes"][-1]["state"].append(999)
    assert loaded.graph.node("shared").state() == [1]
    assert loaded.evidence["shared"].stat == {"log_lr": math.log(2.0)}
    assert loaded.policy_state == {"visited": ["root", "shared"]}


def test_parallel_edges_keep_distinct_states_and_order():
    state = diamond()
    state.graph.add_edge(Edge("right", "shared", threshold_rule(100.0, None), "second"))
    state = replace(state, edge_states=(*state.edge_states, EdgeState(Decision.REJECT)))
    loaded = load(save(state))
    assert [edge.label for edge in loaded.graph.out_edges("right")] == ["right:shared", "second"]
    assert loaded.edge_states[-1].decision is Decision.REJECT
    assert loaded.graph.out_edges("right")[1].decide(EvidenceState(30.0)) is Decision.PENDING


def test_positive_infinite_evidence_has_an_explicit_json_representation():
    state = replace(diamond(), evidence={"shared": EvidenceState(math.inf, None, 2)})
    saved = save(state)
    assert saved["evidence"]["shared"]["e"] == "inf"
    assert load(json.loads(json.dumps(saved, allow_nan=False))).evidence["shared"].e == math.inf


@dataclass(frozen=True)
class Statistic:
    log_lr: float


def test_arbitrary_statistic_requires_an_explicit_codec():
    state = replace(diamond(), evidence={"shared": EvidenceState(2.0, Statistic(0.5), 1)})
    with pytest.raises(CheckpointError, match="explicit codecs"):
        save(state)
    saved = save(state, encode_stat=lambda value: {"log_lr": value.log_lr})
    loaded = load(saved, decode_stat=lambda value: Statistic(**value))
    assert loaded.evidence == state.evidence


@pytest.mark.parametrize("change", [
    lambda d: d.update(format="sequential-search/checkpoint/999"),
    lambda d: d.update(root="unknown"),
    lambda d: d["nodes"].append(copy.deepcopy(d["nodes"][0])),
    lambda d: d["frontier"].append("unknown"),
    lambda d: d["frontier"].append(d["frontier"][0]),
    lambda d: d["evidence"].update(unknown={"e": 1, "n": 0, "stat": None}),
    lambda d: d["evidence"]["shared"].update(e=-1),
    lambda d: d["evidence"]["shared"].update(e=float("nan")),
    lambda d: d["evidence"]["shared"].update(n=True),
    lambda d: d["edges"][0].update(target="unknown"),
    lambda d: d["edges"][0].update(target="root"),
    lambda d: d["edges"][0].update(decision="resume"),
    lambda d: d["edges"][0].update(decision=[]),
    lambda d: d["edges"][0].update(cost_reserved=-1),
    lambda d: d["edges"][0].update(alpha_reserved=0.01),
    lambda d: d["budgets"].update(cost_left=True),
    lambda d: d["budgets"].update(alpha_left=float("inf")),
    lambda d: d.update(rng_state={1: "not a JSON object key"}),
    lambda d: d["edges"].reverse(),
])
def test_corrupt_snapshot_is_rejected_before_factories_are_called(change):
    data = save(diamond())
    change(data)

    def forbidden(*args):
        pytest.fail("factories must not run for an invalid envelope")

    with pytest.raises(CheckpointError):
        restore(data, decode_node=forbidden, decode_rule=forbidden)


def test_restore_rejects_a_factory_that_changes_node_identity():
    with pytest.raises(CheckpointError, match="canonical_key"):
        restore(save(diamond()), decode_node=lambda key, data: Counter("different"),
                decode_rule=lambda payload: threshold_rule(*payload))


def test_capture_rejects_changed_live_identity_or_missing_edge_state():
    state = diamond()
    state.graph.node("shared").name = "moved"
    with pytest.raises(CheckpointError, match="canonical_key"):
        save(state)
    with pytest.raises(CheckpointError, match="one entry per graph edge"):
        save(replace(diamond(), edge_states=()))


def test_empty_and_single_node_graphs():
    state = SearchState(SearchGraph(), Budgets(0.05, 10), (), {}, ())
    with pytest.raises(CheckpointError, match="empty graph"):
        save(state)
    state.graph.add_node(Counter("root"))
    assert load(save(state)).graph.root == "root"


def test_checkpoint_layer_roundtrips_without_site_packages_or_upstream():
    source = Path(__file__).resolve().parents[1] / "src"
    code = """
import importlib.util
import sys
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
assert importlib.util.find_spec('sequential_analysis') is None
from sequential_search.core.graph import SearchGraph
from sequential_search.io.checkpoint import SearchState, checkpoint, restore
from sequential_search.policy.base import Budgets
def node(key):
    return SimpleNamespace(name=key, canonical_key=lambda: key, cost=lambda: 1)
graph = SearchGraph()
graph.add_node(node('root'))
state = SearchState(graph, Budgets(0.05, 10), ('root',), {}, ())
data = checkpoint(state, encode_node=lambda n: {}, encode_rule=lambda r: {})
loaded = restore(data, decode_node=lambda key, payload: node(key), decode_rule=lambda r: None)
assert loaded.graph.root == 'root'
assert loaded.budgets == state.budgets
assert loaded.frontier == state.frontier
"""
    subprocess.run([sys.executable, "-S", "-c", code, str(source)], check=True,
                   capture_output=True, text=True)
