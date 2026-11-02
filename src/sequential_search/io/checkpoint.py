"""Versioned search snapshots, independent of application node and rule types.

Factories are supplied by the caller, never imported from checkpoint data.
An envelope embeds node checkpoints without interpreting them (in particular,
the upstream Run checkpoint belongs inside the ProcedureNode payload).
Loading preserves WITHDRAW; it does not execute a RESUME transition or refund
any budget. Preserving accounting is not a proof of whole-graph error control.
"""
from __future__ import annotations

import json
import math
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sequential_search.core.edge import Decision, Edge, EvidenceState, StoppingRule
from sequential_search.core.graph import SearchGraph
from sequential_search.core.node import Node
from sequential_search.policy.base import Budgets

FORMAT = "sequential-search/checkpoint/1"


class CheckpointError(ValueError):
    """The snapshot is unsupported, inconsistent, or not JSON-serializable."""


@dataclass(frozen=True)
class EdgeState:
    """Lifecycle and outstanding reservations of an edge, in graph order."""

    decision: Decision = Decision.PENDING
    alpha_reserved: float = 0.0
    cost_reserved: float = 0.0


@dataclass(frozen=True)
class SearchState:
    """State needed to continue a search; no traversal algorithm is implied.

    Edge positions follow graph node insertion order, then out_edges order;
    parallel edges remain distinct. Evidence is stored once per canonical node.
    RNG and policy payloads are JSON values owned by their respective callers.
    """

    graph: SearchGraph
    budgets: Budgets
    frontier: tuple[str, ...]
    evidence: Mapping[str, EvidenceState]
    edge_states: tuple[EdgeState, ...]
    rng_state: Any = None
    policy_state: Any = None


def _identity(value: Any) -> Any:
    return value


def checkpoint(
    state: SearchState,
    *,
    encode_node: Callable[[Node], Any],
    encode_rule: Callable[[StoppingRule], Any],
    encode_stat: Callable[[Any], Any] = _identity,
) -> dict[str, Any]:
    """Capture an isolated JSON envelope using explicit application codecs.

    encode_stat defaults to JSON values; arbitrary EvidenceState.stat objects
    require an encoder and corresponding restore decoder. Tuples become JSON
    arrays, so an RNG owner must restore its own required representation.
    """
    graph = state.graph
    node_keys = tuple(graph.keys())
    nodes = []
    for key in node_keys:
        node = graph.node(key)
        if node.canonical_key() != key:
            raise CheckpointError(f"node {key!r}: canonical_key changed after insertion")
        nodes.append({"key": key, "state": encode_node(node)})
    edges = [edge for key in node_keys for edge in graph.out_edges(key)]
    if len(edges) != len(state.edge_states):
        raise CheckpointError("edge_states must contain one entry per graph edge")
    try:
        root = graph.root
    except RuntimeError as exc:
        raise CheckpointError("cannot checkpoint an empty graph") from exc
    envelope = {
        "format": FORMAT,
        "root": root,
        "nodes": nodes,
        "edges": [
            {
                "source": edge.source, "target": edge.target,
                "label": edge.label, "dependency_scope": edge.dependency_scope,
                "rule": encode_rule(edge.rule),
                "decision": item.decision.value,
                "alpha_reserved": item.alpha_reserved,
                "cost_reserved": item.cost_reserved,
            }
            for edge, item in zip(edges, state.edge_states)
        ],
        "frontier": list(state.frontier),
        "evidence": {
            key: {"e": "inf" if value.e == math.inf else value.e,
                  "stat": encode_stat(value.stat), "n": value.n}
            for key, value in state.evidence.items()
        },
        "budgets": {
            name: getattr(state.budgets, name)
            for name in ("alpha_left", "cost_left", "alpha_reserved", "cost_reserved")
        },
        "rng_state": state.rng_state,
        "policy_state": state.policy_state,
    }
    envelope = _json_copy(envelope)
    _validate(envelope)
    return envelope


def restore(
    envelope: dict[str, Any],
    *,
    decode_node: Callable[[str, Any], Node],
    decode_rule: Callable[[Any], StoppingRule],
    decode_stat: Callable[[Any], Any] = _identity,
) -> SearchState:
    """Validate first, then reconstruct a new graph using caller factories.

    No existing graph or budget is mutated. Factories receive isolated payloads;
    they are responsible for restoring and validating their own opaque state.
    """
    data = _json_copy(envelope)
    _validate(data)
    graph = SearchGraph(root=data["root"])
    for record in data["nodes"]:
        key = record["key"]
        node = decode_node(key, record["state"])
        if node.canonical_key() != key:
            raise CheckpointError(f"restored node {key!r}: canonical_key does not match")
        graph.add_node(node)
    for record in data["edges"]:
        rule = decode_rule(record["rule"])
        if not isinstance(rule, StoppingRule):
            raise CheckpointError("decoded rule must implement StoppingRule")
        graph.add_edge(Edge(record["source"], record["target"], rule,
                            record["label"], record["dependency_scope"]))
    return SearchState(
        graph=graph,
        budgets=Budgets(**data["budgets"]),
        frontier=tuple(data["frontier"]),
        evidence={
            key: EvidenceState(math.inf if record["e"] == "inf" else record["e"],
                               decode_stat(record["stat"]), record["n"])
            for key, record in data["evidence"].items()
        },
        edge_states=tuple(
            EdgeState(Decision(record["decision"]), record["alpha_reserved"], record["cost_reserved"])
            for record in data["edges"]
        ),
        rng_state=data["rng_state"], policy_state=data["policy_state"],
    )


def _json_copy(value: Any) -> Any:
    # Strict JSON forbids NaN/Infinity in opaque payloads, preserves float bits,
    # and detaches the snapshot from mutable values owned by a live node.
    def keys(item: Any) -> None:
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise CheckpointError("checkpoint object keys must be strings")
            for child in item.values():
                keys(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                keys(child)

    try:
        keys(value)
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        raise CheckpointError(f"checkpoint requires finite JSON values and explicit codecs: {exc}") from exc


def _fields(value: Any, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != expected:
        raise CheckpointError(f"{where}: expected fields {sorted(expected)}")
    return value


def _number(value: Any, where: str) -> None:
    if type(value) not in (int, float) or value < 0:
        raise CheckpointError(f"{where}: expected a finite non-negative number")
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise CheckpointError(f"{where}: expected a finite non-negative number")


def _validate(data: Any) -> None:
    _fields(data, {"format", "root", "nodes", "edges", "frontier", "evidence",
                   "budgets", "rng_state", "policy_state"}, "checkpoint")
    if data["format"] != FORMAT:
        raise CheckpointError(f"unsupported checkpoint format: {data['format']!r}")
    if not isinstance(data["nodes"], list) or not data["nodes"]:
        raise CheckpointError("nodes: expected a non-empty list")
    keys = set()
    for node in data["nodes"]:
        _fields(node, {"key", "state"}, "node")
        key = node["key"]
        if not isinstance(key, str) or not key or key in keys:
            raise CheckpointError("node keys must be non-empty and unique")
        keys.add(key)
    root = data["root"]
    if not isinstance(root, str) or root not in keys:
        raise CheckpointError("root must reference a saved node")
    frontier = data["frontier"]
    if (not isinstance(frontier, list)
            or any(not isinstance(key, str) or key not in keys for key in frontier)
            or len(set(frontier)) != len(frontier)):
        raise CheckpointError("frontier must contain unique saved node keys")
    if not isinstance(data["evidence"], dict) or not data["evidence"].keys() <= keys:
        raise CheckpointError("evidence must reference saved nodes")
    for record in data["evidence"].values():
        _fields(record, {"e", "stat", "n"}, "evidence")
        if record["e"] != "inf":
            _number(record["e"], "evidence.e")
        if type(record["n"]) is not int or record["n"] < 0:
            raise CheckpointError("evidence.n must be a non-negative integer")
    budget_names = {"alpha_left", "cost_left", "alpha_reserved", "cost_reserved"}
    _fields(data["budgets"], budget_names, "budgets")
    for name, value in data["budgets"].items():
        _number(value, f"budgets.{name}")
    if not isinstance(data["edges"], list):
        raise CheckpointError("edges: expected a list")
    adjacent: dict[str, list[str]] = {key: [] for key in keys}
    incoming = dict.fromkeys(keys, 0)
    order = {node["key"]: index for index, node in enumerate(data["nodes"])}
    last_source = -1
    for edge in data["edges"]:
        _fields(edge, {"source", "target", "label", "dependency_scope", "rule",
                       "decision", "alpha_reserved", "cost_reserved"}, "edge")
        for field in ("source", "target"):
            if not isinstance(edge[field], str) or edge[field] not in keys:
                raise CheckpointError("edge endpoints must reference saved nodes")
        # The array position identifies an edge. Reject a reordered manifest
        # that would change those identities when reconstructed by SearchGraph.
        source_order = order[edge["source"]]
        if source_order < last_source:
            raise CheckpointError("edges must follow node insertion order")
        last_source = source_order
        if any(not isinstance(edge[field], str) for field in ("label", "dependency_scope")):
            raise CheckpointError("edge label and dependency_scope must be strings")
        if (not isinstance(edge["decision"], str)
                or edge["decision"] not in {"pending", "accept", "reject", "withdraw"}):
            raise CheckpointError("edge decision must be a lifecycle state; RESUME is a command")
        for name in ("alpha_reserved", "cost_reserved"):
            _number(edge[name], f"edge.{name}")
        adjacent[edge["source"]].append(edge["target"])
        incoming[edge["target"]] += 1
    queue = deque(key for key in keys if incoming[key] == 0)
    count = 0
    while queue:
        key = queue.popleft()
        count += 1
        for target in adjacent[key]:
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    if count != len(keys):
        raise CheckpointError("checkpoint graph must be acyclic")
    for name in ("alpha_reserved", "cost_reserved"):
        allocated = sum(edge[name] for edge in data["edges"])
        if not math.isclose(allocated, data["budgets"][name], rel_tol=1e-12, abs_tol=1e-15):
            raise CheckpointError(f"{name}: edge reservations do not match aggregate budget")
