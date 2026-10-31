"""Адаптер Procedure из sequential-analysis -> Node + EvidenceState (ADR-003, слой 2).

Здесь единственное место ядра, которое знает про upstream. Адаптер тонкий:
он не реализует статистику, а связывает контракт узла с контрактом Run.

Инвариант degenerate anchor требует численного совпадения с standalone-прогоном,
поэтому `ProcedureNode` обязан использовать ровно один `Run` на узел и передавать
наблюдения без преобразования (см. Observation в core/node.py).
"""
from __future__ import annotations

from typing import Any

from sequential_search.core.edge import Decision, EvidenceState
from sequential_search.core.node import Observation


class ProcedureNode:
    """Узел-эксперимент поверх последовательной процедуры sequential-analysis.

    Реализует протокол core.node.Node. Конструируется лениво: сам Run создаётся
    при первом шаге, чтобы импорт ядра не требовал тяжёлого upstream.
    """

    def __init__(self, name: str, procedure_factory, *, seed: int | None = None,
                 cost_per_step: float = 1.0, canonical_key: str | None = None) -> None:
        self.name = name
        self._procedure_factory = procedure_factory   # callable() -> Procedure
        self._seed = seed
        self._cost = float(cost_per_step)
        self._canonical_key = canonical_key
        self._run = None
        self._t = 0
        self._last_output: Any = None
        self._last_values: dict[str, Any] = {}

    # --- Node protocol -------------------------------------------------
    def step(self) -> Observation:
        """Синхронизировать счётчик и вернуть последнее принятое наблюдение.

        Для ProcedureNode данные поступают извне через feed(), поэтому step()
        существует ради совместимости с протоколом Node (например, для узлов,
        генерирующих собственные наблюдения) и не двигает статистику вперёд.
        """
        return Observation(t=self._t, values=dict(self._last_values))

    def feed(self, values: dict[str, Any]) -> EvidenceState:
        """Подать наблюдение процедуре и вернуть накопленные улики ребра.

        Это основной путь:Traversal вызывает его вместо «слепого» step(),
        потому что данные приходят извне (слайс томографии, ход агента, шаг
        вывода), а не генерируются узлом.
        """
        run = self._ensure_run()
        event = run.step(values)
        self._t = event.t
        self._last_values = dict(values)
        self._last_output = event.output
        return self.evidence()

    def state(self) -> Any:
        return self._ensure_run().state

    def cost(self) -> float:
        return self._cost

    def canonical_key(self) -> str:
        return self._canonical_key or f"{self.name}@{self._t}"

    def is_terminal(self) -> bool:
        return self._run is not None and self._run.terminal

    # --- улики ---------------------------------------------------------
    def evidence(self) -> EvidenceState:
        """e-value из log LR процедуры (для SPRT/мартингальных процедур)."""
        out = self._last_output
        if out is None:
            return EvidenceState(e=1.0, stat=None, n=0)
        llr = getattr(out, "llr", None)
        stat = llr if llr is not None else getattr(out, "stat", None)
        e = _exp_if_finite(llr) if llr is not None else 1.0
        n = int(getattr(out, "n", self._t))
        return EvidenceState(e=e, stat=out, n=n)

    def decision(self) -> Decision:
        d = getattr(self._last_output, "decision", None)
        if d in ("reject_h0", "accept_h1"):
            return Decision.ACCEPT
        if d in ("accept_h0", "reject_h1"):
            return Decision.REJECT
        return Decision.PENDING

    # --- internals -----------------------------------------------------
    def _ensure_run(self):
        if self._run is None:
            from sequential_analysis import Run  # локальный импорт: [core] extra без upstream
            proc = self._procedure_factory()
            self._run = Run(proc, seed=self._seed)
            self._run.start()
        return self._run


def _exp_if_finite(x: float | None) -> float:
    """log LR -> e-value с защитой от переполнения (e-валюта ядра)."""
    import math

    if x is None:
        return 1.0
    if x > 700:
        return math.inf
    if x < -745:
        return 0.0
    return math.exp(x)


def wald_thresholds(alpha: float, beta: float) -> tuple[float, float]:
    """Границы Вальда в e-валютe для вырожденного случая (SPRT).

    upper = exp(log((1-beta)/alpha)) — порог отвержения H0;
    lower = exp(log(beta/(1-alpha))) — порог принятия H0.

    Возвращает именно экспоненты, потому что EvidenceState.e хранит e-value,
    а не log LR; совпадение с `SPRT.upper/lower` из sequential-analysis
    проверяется тестом degenerate anchor.
    """
    import math

    if not (0 < alpha < 1 and 0 < beta < 1 and alpha + beta < 1):
        raise ValueError("need alpha, beta in (0,1) with alpha + beta < 1")
    return math.exp(math.log((1.0 - beta) / alpha)), math.exp(math.log(beta / (1.0 - alpha)))
