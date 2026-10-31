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
      параметризацией (спецификация зафиксирована кодом
      tests/test_degenerate_anchor.py; файл docs/spec-degenerate-anchor.md
      был обещан в ADR-003 следствие 1, но не создан — см. примечание там же).
  E4  WITHDRAW существует в контракте, но не может быть порождём ни одним
      встроенным правилом (ADR-005, дыра D). Порождающий его механизм —
      cost-to-go критерий на уровне traversal/budget, а не StoppingRule:
      решение «встать» принимается по стоимости продолжения, а не по силе
      улик. Попытка вернуть WITHDRAW из правила — ошибка программы, поэтому
      Edge.decide() её перехватывает.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    PENDING = "pending"
    WITHDRAW = "withdraw"
    RESUME = "resume"


#: Терминальные исхода ребра. RESUME терминальным не является: это возвращение
#: в PENDING (ADR-006), поэтому он отсутствует в этом множестве.
TERMINAL_DECISIONS: frozenset[Decision] = frozenset(
    {Decision.ACCEPT, Decision.REJECT, Decision.WITHDRAW}
)

#: Исходы, при которых доля α, выделенная на ребро, может быть возвращена в
#: общий пул (ADR-005 следствие 2, ADR-006). REJECT её не возвращает: ложное
#: отвержение — это и есть ошибка, за которую бюджет платит заранее.
REFUNDABLE_DECISIONS: frozenset[Decision] = frozenset(
    {Decision.WITHDRAW}
)


class RuleContractError(RuntimeError):
    """StoppingRule вернул исход, который ему порождать запрещено (E4)."""


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
    """Чистое отображение улик -> решение (E1).

    Запрещено возвращать WITHDRAW/RESUME: первый порождается только
    cost-to-go критерием вне правила, второй — только внешним событием
    возобновления (E4).
    """

    def decide(self, evidence: EvidenceState) -> Decision:
        ...


@dataclass(frozen=True)
class Edge:
    """Ребро = пара (правило остановки, семантическая метка направления).

    `dependency_scope` — зарезервированное поле (ADR-004, дыра A): идентификатор
    среды/источника, наблюдения внутри которого коррелированы. Семантика пока
    не определена и на решения не влияет; поле введено сейчас, чтобы появление
    калибровки бюджета под зависимые проверки не ломало контракт. Пустая строка
    означает «независимое ребро» (текущее поведение по умолчанию).
    """

    source: str
    target: str
    rule: StoppingRule
    label: str = ""
    dependency_scope: str = ""

    def decide(self, evidence: EvidenceState) -> Decision:
        d = self.rule.decide(evidence)
        if not isinstance(d, Decision):
            raise TypeError(f"edge {self.source}->{self.target}: rule returned {d!r}")
        if d in (Decision.WITHDRAW, Decision.RESUME):
            raise RuleContractError(
                f"edge {self.source}->{self.target}: StoppingRule вернул {d.value}; "
                "WITHDRAW порождается cost-to-go критерием вне правила, "
                "RESUME — внешним событием возобновления (инвариант E4)"
            )
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
