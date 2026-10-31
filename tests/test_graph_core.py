"""Юнит-тесты слоя контрактов (ADR-003, слой 1). Работают БЕЗ upstream."""
from __future__ import annotations

import pytest

from sequential_search.core.edge import Decision, Edge, EvidenceState, threshold_rule
from sequential_search.core.graph import SearchGraph
from sequential_search.core.node import Observation, check_node
from sequential_search.policy.base import Budgets


class FakeNode:
    def __init__(self, name: str, key: str | None = None, cost: float = 1.0) -> None:
        self.name = name
        self._key = key or name
        self._cost = cost

    def step(self) -> Observation:
        return Observation(t=1, values={"x": 0.0})

    def state(self):
        return self._key

    def cost(self) -> float:
        return self._cost

    def canonical_key(self) -> str:
        return self._key

    def is_terminal(self) -> bool:
        return False


def test_observation_rejects_t_zero():
    with pytest.raises(ValueError):
        Observation(t=0, values={"x": 1})


def test_check_node_rejects_negative_cost():
    with pytest.raises(ValueError):
        check_node(FakeNode("n", cost=-1.0))


def test_dag_merging_no_double_counting():
    """Два узла с одним canonical_key — один эксперимент (инвариант 5)."""
    g = SearchGraph()
    a = g.add_node(FakeNode("path1", key="equation::x+y=2"))
    b = g.add_node(FakeNode("path2", key="equation::x+y=2"))
    assert a == b and len(g) == 1


def test_degenerate_graph_is_recognized():
    g = SearchGraph()
    root = g.add_node(FakeNode("root"))
    leaf = g.add_node(FakeNode("leaf"))
    g.add_edge(Edge(root, leaf, threshold_rule(19.0, 0.111)))
    assert g.is_degenerate()


def test_unknown_edge_endpoint_raises():
    g = SearchGraph()
    root = g.add_node(FakeNode("root"))
    with pytest.raises(KeyError):
        g.add_edge(Edge(root, "ghost", threshold_rule(19.0, None)))


def test_threshold_rule_three_way():
    rule = threshold_rule(upper=19.0, lower=0.111)
    assert rule.decide(EvidenceState(e=1.0)) is Decision.PENDING
    assert rule.decide(EvidenceState(e=20.0)) is Decision.ACCEPT
    assert rule.decide(EvidenceState(e=0.05)) is Decision.REJECT


def test_evidence_state_rejects_negative():
    with pytest.raises(ValueError):
        EvidenceState(e=-1.0)


def test_budgets_are_two_dimensional():
    b = Budgets(alpha_left=0.05, cost_left=100.0)
    assert b.can_afford(100.0) and not b.can_afford(101.0)
    # исчерпание ресурса не меняет α-бюджет и наоборот
    assert Budgets(0.0, 100.0).can_afford(1.0)
