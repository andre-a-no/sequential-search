"""SearchGraph: DAG с канонизацией узлов и динамическим раскрытием (ADR-002).

Инвариант 5 README (no double counting) реализуется здесь: узел адресуется
`canonical_key`, поэтому два разных пути вывода, приведшие к эквивалентному
состоянию, — ОДИН эксперимент с одними накопленными уликами.
"""
from __future__ import annotations

from collections.abc import Iterator

from sequential_search.core.edge import Edge
from sequential_search.core.node import Node, check_node


class SearchGraph:
    def __init__(self, root: str | None = None) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, list[Edge]] = {}
        self._root = root

    # --- построение ----------------------------------------------------
    def add_node(self, node: Node) -> str:
        """Добавить узел или вернуть существующий по canonical_key (дедупликация)."""
        check_node(node)
        key = node.canonical_key()
        if key in self._nodes and self._nodes[key] is not node:
            # повторный вход в тот же эксперимент: улики НЕ сбрасываются и НЕ дублируются
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
        """Динамическое раскрытие (кейс 3: поток гипотез бесконечен)."""
        for n in nodes:
            self.add_node(n)
        for e in edges:
            self.add_edge(e)

    # --- доступ --------------------------------------------------------
    @property
    def root(self) -> str:
        if self._root is None:
            raise RuntimeError("empty graph has no root")
        return self._root

    def is_degenerate(self) -> bool:
        """Граф вырожден (= классический бинарный тест): ровно одно ребро из корня."""
        return len(self._nodes) == 2 and len(self._edges.get(self.root, ())) == 1

    def node(self, key: str) -> Node:
        return self._nodes[key]

    def out_edges(self, key: str) -> tuple[Edge, ...]:
        return tuple(self._edges.get(key, ()))

    def keys(self) -> Iterator[str]:
        return iter(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)
