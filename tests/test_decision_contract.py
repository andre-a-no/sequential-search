"""Контракт четвёртого/пятого исхода (ADR-005 дыра D, ADR-006).

Спецификация, а не набор проверок «на всякий случай». Три утверждения, которые
нельзя нарушить без потери смысла WITHDRAW/RESUME:

1. StoppingRule физически не способен породить WITHDRAW/RESUME. Это граница
   ответственности: улики решают про гипотезу, стоимость решает про игру.
2. WITHDRAW — терминальный, RESUME — нет. Если RESUME станет терминальным,
   возобновление превратится в новый поиск с обнулёнными уликами.
3. Возврат α возможен ровно в пределах зарезервированного. Иначе бюджет
   печатает α из воздуха и global guarantee ложна.
"""
from __future__ import annotations

import pytest

from sequential_search.core.edge import (
    Decision,
    Edge,
    EvidenceState,
    RuleContractError,
    TERMINAL_DECISIONS,
    threshold_rule,
)
from sequential_search.policy.base import Budgets


class _BadRule:
    """Правило-нарушитель: пытается решить про стоимость через улики."""

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
    """WITHDRAW не может напечатать α — ровно то, ради чего введено reserved."""
    b = Budgets(alpha_left=0.04, cost_left=70.0, alpha_reserved=0.01, cost_reserved=30.0)
    with pytest.raises(ValueError, match="B2"):
        b.refund(alpha=0.02, cost=0.0)
    with pytest.raises(ValueError, match="B2"):
        b.refund(alpha=0.0, cost=31.0)


def test_negative_budget_invalid() -> None:
    with pytest.raises(ValueError):
        Budgets(alpha_left=-0.01, cost_left=1.0)
