"""Политика обхода = чистая функция frontier × бюджеты -> следующий узел.

Определение (ADR-003, слой 4): политика *guarantee-invariant*, если для любой
последовательности наблюдений распределение ошибок обхода (FWER/FDR, ARL) не
зависит от выбора, сделанного политикой. Формально: решение на ребре есть
функция только накопленных улик этого ребра (инвариант E1), а политика влияет
лишь на то, КАКИЕ улики успели накопиться к моменту остановки по бюджету.

Следствие: политика обязана вызывать `node.feed(values)` и читать
`edge.decide(evidence)`, но не имеет права порождать решения сама.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Budgets:
    """Двумерный бюджет (ADR-001): риск и ресурс не конвертируются друг в друга."""

    alpha_left: float     # оставшийся α-бюджет (e-value calibration)
    cost_left: float      # оставшаяся стоимость (шаги, байты, токены, секунды)

    def can_afford(self, cost: float) -> bool:
        return cost <= self.cost_left + 1e-12


class Policy(Protocol):
    def next_node(self, frontier: Sequence[str], budgets: Budgets) -> str | None:
        """Вернуть ключ узла или None (остановка). Не должен ничего накапливать."""
        ...
