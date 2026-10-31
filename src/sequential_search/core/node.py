"""Узел графа = эксперимент (ADR-001). Никакой статистики в этом модуле.

Инварианты, проверяемые runtime (ADR-003, слой 1):
  N1  step() возвращает новый Observation; состояние узла неизменяемо
      (immutable value), шаг не модифицирует аргументы — транзакционность
      наследуется от Procedure из sequential-analysis.
  N2  cost() >= 0 и конечна. Стоимость наблюдения может различаться по уровням
      (кейс 5: тонкий срез дороже усреднённого), поэтому она функция состояния,
      а не константа ребра.
  N3  canonical_key() определён для всякого посещённого состояния: два узла с
      одинаковым ключом — один и тот же эксперимент (инвариант 5, no double
      counting). Для чистого дерева ключ уникален по построению.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class Observation:
    """Одно наблюдение эксперимента: тик + именованные значения.

    Совпадает по семантике со словарём входа `Procedure.step` в
    sequential-analysis (`{'x': ...}`), поэтому адаптер слоя stats не
    преобразует данные, а только маршрутизирует их.
    """

    t: int
    values: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.t < 1:
            raise ValueError(f"Observation.t must be >= 1, got {self.t}")
        if not isinstance(self.values, Mapping):
            raise TypeError("Observation.values must be a mapping")


@runtime_checkable
class Node(Protocol):
    """Эксперимент, порождающий поток наблюдений.

    НЕ является: данными, гипотезой, «скором» агента (ADR-001).
    """

    name: str

    def step(self) -> Observation:
        """Сделать одно наблюдение. Идемпотентность не требуется, чистота — да."""
        ...

    def state(self) -> Any:
        """Текущее состояние узла как immutable value (для чекпоинтинга)."""
        ...

    def cost(self) -> float:
        """Стоимость СЛЕДУЮЩЕГО шага (N2)."""
        ...

    def canonical_key(self) -> str:
        """Ключ канонической формы состояния (N3)."""
        ...

    def is_terminal(self) -> bool:
        """Поглощающее состояние: дальнейшие шаги запрещены."""
        ...


def check_node(node: Node) -> None:
    """Проверить инварианты N1-N3 на текущем состоянии узла. Бросает ValueError."""
    key = node.canonical_key()
    if not isinstance(key, str) or not key:
        raise ValueError(f"node '{node.name}': canonical_key must be non-empty str")
    c = node.cost()
    if not (isinstance(c, (int, float)) and c >= 0):
        raise ValueError(f"node '{node.name}': cost must be a non-negative number, got {c!r}")
