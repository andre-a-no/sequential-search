"""Contract of the fourth/fifth outcome (ADR-005 hole D, ADR-006).

A specification, not a set of "just in case" checks. Three claims that cannot be
violated without WITHDRAW/RESUME losing their meaning:

1. A StoppingRule is physically incapable of producing WITHDRAW/RESUME. This is
   the boundary of responsibility: evidence decides about the hypothesis, cost
   decides about the game.
2. WITHDRAW is terminal, RESUME is not. If RESUME became terminal, resumption
   would turn into a new search with zeroed-out evidence.
3. A refund is possible exactly within what was reserved. Otherwise the budget
   prints alpha out of thin air and the global guarantee is false.
"""
from __future__ import annotations

import pytest

from sequential_search.graph.edge import (
    Decision,
    Edge,
    EvidenceState,
    RuleContractError,
    TERMINAL_DECISIONS,
    threshold_rule,
)
from sequential_search.policy.base import Budgets


class _BadRule:
    """A rule-breaker: tries to decide about cost through evidence."""

    def __init__(self, verdict: Decision) -> None:
        self._verdict = verdict

    def decide(self, evidence: EvidenceState) -> Decision:
        return self._verdict


def _edge(rule) -> Edge:
    return Edge(source="a", target="b", rule=rule)


@pytest.mark.parametrize("verdict", [Decision.WITHDRAW, Decision.RESUME])
def test_rule_cannot_produce_cost_side_decisions(verdict: Decision) -> None:
    e = _edge(_BadRule(verdict))
    with pytest.raises(RuleContractError):
        e.decide(EvidenceState(e=1.0))


def test_threshold_rule_never_emits_withdraw_or_resume() -> None:
    rule = threshold_rule(upper=10.0, lower=0.1)
    seen = {rule.decide(EvidenceState(e=x)) for x in (0.01, 0.5, 3.0, 99.0)}
    assert seen <= {Decision.ACCEPT, Decision.REJECT, Decision.PENDING}


def test_terminal_membership() -> None:
    assert Decision.WITHDRAW in TERMINAL_DECISIONS
    assert Decision.RESUME not in TERMINAL_DECISIONS
    assert Decision.PENDING not in TERMINAL_DECISIONS


def test_reserve_then_refund_is_conservative() -> None:
    b = Budgets(alpha_left=0.05, cost_left=100.0)
    b2 = b.reserve(alpha=0.01, cost=30.0)
    assert b2.alpha_total == pytest.approx(0.05)
    assert b2.cost_total == pytest.approx(100.0)
    b3 = b2.refund(alpha=0.01, cost=30.0)
    assert b3.alpha_left == pytest.approx(0.05)
    assert b3.cost_left == pytest.approx(100.0)
    assert b3.alpha_reserved == pytest.approx(0.0)


def test_overreserve_rejected_b1() -> None:
    b = Budgets(alpha_left=0.05, cost_left=100.0)
    with pytest.raises(ValueError, match="B1"):
        b.reserve(alpha=0.06, cost=1.0)
    with pytest.raises(ValueError, match="B1"):
        b.reserve(alpha=0.01, cost=101.0)


def test_overrefund_rejected_b2() -> None:
    """WITHDRAW cannot print alpha -- exactly why `reserved` was introduced."""
    b = Budgets(alpha_left=0.04, cost_left=70.0, alpha_reserved=0.01, cost_reserved=30.0)
    with pytest.raises(ValueError, match="B2"):
        b.refund(alpha=0.02, cost=0.0)
    with pytest.raises(ValueError, match="B2"):
        b.refund(alpha=0.0, cost=31.0)


def test_negative_budget_invalid() -> None:
    with pytest.raises(ValueError):
        Budgets(alpha_left=-0.01, cost_left=1.0)
