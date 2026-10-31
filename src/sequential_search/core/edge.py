"""Ребро графа = stopping rule (ADR-001). Булев предикат — вырожденный случай.

Инварианты:
  E1  decide() чиста: решение зависит только от накопленных улик и порога,
      переданных аргументами, а не от порядка обхода или истории политики.
      Иначе global guarantee (инвариант 1 README) недоказуем.
  E2  Три исхода: accept / reject / pending. pending допускает сколь угодно
      длинное накопление — anytime-valid ребро никогда не «заканчивается»
      по таймауту (кейс 6, perpetual traversal).
  E3  Классический бинарный тест — это Edge с одним источником улик и двумя
      непустыми исходами. Special-case в коде запрещён: он получается
      параметризацией (degenerate anchor, tests/spec_degenerate_anchor.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    PENDING = "pending"


@dataclass(frozen=True)
class EvidenceState:
    """Накопленные улики ребра. Валюта — e-value (ADR-003, слой 2).

    `e` >= 1 трактуется как сила улик против null; `stat` хранит исходную
    величину процедуры (log LR для SPRT и т.п.) для совместимости с
    чекпоинтами sequential-analysis.
    """

    e: float
    stat: Any = None
    n: int = 0

    def __post_init__(self) -> None:
        if self.e < 0:
            raise ValueError(f"EvidenceState.e must be non-negative, got {self.e}")
        if self.n < 0:
            raise ValueError(f"EvidenceState.n must be non-negative, got {self.n}")


@runtime_checkable
class StoppingRule(Protocol):
    """Чистое отображение улик -> решение (E1)."""

    def decide(self, evidence: EvidenceState) -> Decision:
        ...


@dataclass(frozen=True)
class Edge:
    """Ребро = пара (правило остановки, семантическая метка направления)."""

    source: str
    target: str
    rule: StoppingRule
    label: str = ""

    def decide(self, evidence: EvidenceState) -> Decision:
        d = self.rule.decide(evidence)
        if not isinstance(d, Decision):
            raise TypeError(f"edge {self.source}->{self.target}: rule returned {d!r}")
        return d


def threshold_rule(upper: float, lower: float | None) -> "_ThresholdRule":
    """Каноническое правило: e >= upper -> accept, e <= lower -> reject.

    Для вырожденного случая (SPRT) вызывается с upper = exp(log((1-b)/a)),
    lower = exp(log(b/(1-a))) — см. degenerate anchor.
    """
    return _ThresholdRule(upper, lower)


@dataclass(frozen=True)
class _ThresholdRule:
    upper: float
    lower: float | None

    def decide(self, evidence: EvidenceState) -> Decision:
        if evidence.e >= self.upper:
            return Decision.ACCEPT
        if self.lower is not None and evidence.e <= self.lower:
            return Decision.REJECT
        return Decision.PENDING
