"""SearchGraph: a DAG with node canonicalisation and dynamic expansion (ADR-002).

README invariant 5 (no double counting) is implemented here: a node is
addressed by `canonical_key`, so two different inference paths that lead to an
equivalent state are ONE experiment with ONE accumulated body of evidence.
"""
from __future__ import annotations

from collections.abc import Iterator

from sequential_search.graph.edge import Edge
from sequential_search.graph.node import Node, check_node


class SearchGraph:
    def __init__(self, root: str | None = None) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, list[Edge]] = {}
        self._root = root

    # --- construction --------------------------------------------------
    def add_node(self, node: Node) -> str:
        """Add a node, or return the existing one by canonical_key (dedup)."""
        check_node(node)
        key = node.canonical_key()
        if key in self._nodes and self._nodes[key] is not node:
            # Re-entry into the same experiment: evidence is neither reset nor
            # duplicated.
            return key
        self._nodes[key] = node
        self._edges.setdefault(key, [])
        if self._root is None:
            self._root = key
        return key

    def add_edge(self, edge: Edge) -> None:
        for endpoint in (edge.source, edge.target):
            if endpoint not in self._nodes:
                raise KeyError(f"unknown node {endpoint!r} on edge {edge.source}->{edge.target}")
        self._edges[edge.source].append(edge)

    def expand(self, source: str, nodes: list[Node], edges: list[Edge]) -> None:
        """Dynamic expansion (case 3: the hypothesis stream is unbounded)."""
        for n in nodes:
            self.add_node(n)
        for e in edges:
            self.add_edge(e)

    # --- access ----------------------------------------------------------
    @property
    def root(self) -> str:
        if self._root is None:
            raise RuntimeError("empty graph has no root")
        return self._root

    def is_degenerate(self) -> bool:
        """Graph is degenerate (= a classical binary test): exactly one edge from the root."""
        return len(self._nodes) == 2 and len(self._edges.get(self.root, ())) == 1

    def node(self, key: str) -> Node:
        return self._nodes[key]

    def out_edges(self, key: str) -> tuple[Edge, ...]:
        return tuple(self._edges.get(key, ()))

    def keys(self) -> Iterator[str]:
        return iter(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)
