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
    """Двумерный бюджет (ADR-001): риск и ресурс не конвертируются друг в друга.

    Оба измерения *возобновляемы* (ADR-006): WITHDRAW возвращает в пул долю α,
    выделенную на остановленную ветку, и её же стоимость. Возврат возможен
    только потому, что α расходуется как **резервирование** под возможную
    ошибку на этом ребре, а не как невозвратная трата; если ребро закрыто без
    вынесения reject/accept, резерв не использован.

    Инвариант B1 (непревышение): ни одна операция не позволяет потратить больше,
    чем было выделено — иначе global guarantee теряет смысл.
    Инвариант B2 (корректность возврата): возврат не может превысить ранее
    зарезервированное. Нарушение = ошибка программы, а не «улучшение плана».
    """

    alpha_left: float     # свободный α-бюджет (e-value calibration)
    cost_left: float      # свободная стоимость (шаги, байты, токены, секунды)
    #: сколько α и стоимости currently зарезервировано под открытые рёбра
    alpha_reserved: float = 0.0
    cost_reserved: float = 0.0

    def __post_init__(self) -> None:
        for name in ("alpha_left", "cost_left", "alpha_reserved", "cost_reserved"):
            v = getattr(self, name)
            if v < 0:
                raise ValueError(f"Budgets.{name} must be non-negative, got {v}")

    @property
    def alpha_total(self) -> float:
        return self.alpha_left + self.alpha_reserved

    @property
    def cost_total(self) -> float:
        return self.cost_left + self.cost_reserved

    def can_afford(self, cost: float) -> bool:
        return cost <= self.cost_left + 1e-12

    def reserve(self, alpha: float, cost: float) -> "Budgets":
        """Выделить α и стоимость под ребро/узел. Непревышение — B1."""
        if alpha > self.alpha_left + 1e-12:
            raise ValueError(
                f"reserve(alpha={alpha}) exceeds alpha_left={self.alpha_left} (B1)"
            )
        if cost > self.cost_left + 1e-12:
            raise ValueError(
                f"reserve(cost={cost}) exceeds cost_left={self.cost_left} (B1)"
            )
        return Budgets(
            alpha_left=self.alpha_left - alpha,
            cost_left=self.cost_left - cost,
            alpha_reserved=self.alpha_reserved + alpha,
            cost_reserved=self.cost_reserved + cost,
        )

    def refund(self, alpha: float, cost: float) -> "Budgets":
        """Вернуть неизрасходованное в пул (семантика WITHDRAW). Ограничено B2."""
        if alpha > self.alpha_reserved + 1e-12:
            raise ValueError(
                f"refund(alpha={alpha}) exceeds alpha_reserved={self.alpha_reserved} (B2)"
            )
        if cost > self.cost_reserved + 1e-12:
            raise ValueError(
                f"refund(cost={cost}) exceeds cost_reserved={self.cost_reserved} (B2)"
            )
        return Budgets(
            alpha_left=self.alpha_left + alpha,
            cost_left=self.cost_left + cost,
            alpha_reserved=self.alpha_reserved - alpha,
            cost_reserved=self.cost_reserved - cost,
        )


class Policy(Protocol):
    def next_node(self, frontier: Sequence[str], budgets: Budgets) -> str | None:
        """Вернуть ключ узла или None (остановка по бюджету). Ничего не накапливает.

        Остановка по `None` — это НЕ вывод о данных: это конец обхода из-за
        кончившегося бюджета. Не путать с WITHDRAW (решение отказаться от
        ветки, пока бюджет ещё есть) — ADR-005/006.
        """
        ...
