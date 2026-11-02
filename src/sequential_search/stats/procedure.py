"""Адаптер Procedure из sequential-analysis -> Node + EvidenceState (ADR-003, слой 2).

Здесь единственное место ядра, которое знает про upstream. Адаптер тонкий:
он не реализует статистику, а связывает контракт узла с контрактом Run.

Инвариант degenerate anchor требует численного совпадения с standalone-прогоном,
поэтому `ProcedureNode` обязан использовать ровно один `Run` на узел и передавать
наблюдения без преобразования (см. Observation в core/node.py).
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sequential_search.core.edge import Decision, EvidenceState
from sequential_search.core.node import Observation

if TYPE_CHECKING:
    from sequential_analysis import Run


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
        self._run: Run | None = None
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
        # The identity belongs to the experiment, not to its observation count:
        # SearchGraph keeps this key while the procedure advances and resumes.
        return self._canonical_key or self.name

    def is_terminal(self) -> bool:
        return self._run is not None and self._run.terminal

    # --- улики ---------------------------------------------------------
    def evidence(self) -> EvidenceState:
        """e-value из log LR процедуры (для SPRT/мартингальных процедур)."""
        out = self._last_output
        if out is None:
            return EvidenceState(e=1.0, stat=None, n=0)
        llr = getattr(out, "llr", None)
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

    # --- persistence ---------------------------------------------------
    def checkpoint(self, *, encode_output: Callable[[Any], Any] | None = None) -> dict:
        """Capture the adapter and its unmodified upstream Run checkpoint.

        Outputs need their own codec because upstream encodes procedure state,
        not output objects. Pass an explicit encoder for dataclass/custom
        outputs and the matching decoder to restore(); no Python type names or
        executable factories are loaded from a checkpoint. Plain JSON outputs
        need no codec. Observations must use plain JSON values as well. Taking
        a checkpoint does not initialize a fresh node.
        """
        custom = self._t > 0 and encode_output is not None
        output = (encode_output(self._last_output)
                  if custom and encode_output is not None else self._last_output)
        data = {
            "format": "sequential-search/procedure-node/1",
            "name": self.name,
            "canonical_key": self.canonical_key(),
            "cost_per_step": self._cost,
            "seed": None if self._seed is None else str(self._seed),
            "run": None if self._run is None else self._run.checkpoint(),
            "last_values": self._last_values,
            "output": {"encoding": "custom" if custom else "json", "value": output},
        }
        try:
            result = _json_copy(data)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"ProcedureNode checkpoint requires JSON values; "
                f"pass encode_output for custom outputs: {error}"
            ) from error
        _validate_checkpoint(result)
        return result

    @classmethod
    def restore(cls, procedure_factory, checkpoint: dict, *,
                decode_output: Callable[[Any], Any] | None = None) -> ProcedureNode:
        """Restore with a caller-supplied procedure factory and output decoder.

        Run.restore verifies procedure identity, state, history and RNG. The
        restored adapter is ready for feed(); terminal nodes remain terminal.
        """
        data = _json_copy(checkpoint)
        _validate_checkpoint(data)
        encoded = data["output"]
        if encoded["encoding"] == "custom":
            if decode_output is None:
                raise ValueError("custom output requires decode_output")
            output = decode_output(encoded["value"])
        else:
            output = encoded["value"]
        node = cls(data["name"], procedure_factory,
                   seed=None if data["seed"] is None else int(data["seed"]),
                   cost_per_step=data["cost_per_step"], canonical_key=data["canonical_key"])
        if data["run"] is not None:
            from sequential_analysis import Run

            node._run = Run.restore(procedure_factory(), data["run"])
            node._run.start()
            node._t = node._run.t
        node._last_values = data["last_values"]
        node._last_output = output
        return node

    # --- internals -----------------------------------------------------
    def _ensure_run(self):
        if self._run is None:
            from sequential_analysis import (
                Run,  # локальный импорт: [core] extra без upstream
            )

            proc = self._procedure_factory()
            self._run = Run(proc, seed=self._seed)
            self._run.start()
        return self._run


def _json_copy(value: Any) -> Any:
    """Reject lossy coercions, then detach all mutable checkpoint values."""
    def validate(item):
        if type(item) in (str, int, bool, type(None)):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for part in item:
                validate(part)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for part in item.values():
                validate(part)
            return
        raise ValueError(f"unsupported JSON value: {type(item).__name__}")

    validate(value)
    return json.loads(json.dumps(value, allow_nan=False))


def _validate_checkpoint(data: dict) -> None:
    expected = {"format", "name", "canonical_key", "cost_per_step", "seed", "run", "last_values", "output"}
    if type(data) is not dict or set(data) != expected:
        raise ValueError("invalid ProcedureNode checkpoint fields")
    if data["format"] != "sequential-search/procedure-node/1":
        raise ValueError("unsupported ProcedureNode checkpoint format")
    if any(type(data[name]) is not str or not data[name] for name in ("name", "canonical_key")):
        raise ValueError("name and canonical_key must be non-empty strings")
    cost = data["cost_per_step"]
    try:
        valid_cost = type(cost) in (int, float) and math.isfinite(cost) and cost >= 0
    except OverflowError:
        valid_cost = False
    if not valid_cost:
        raise ValueError("cost_per_step must be finite and non-negative")
    seed = data["seed"]
    if seed is not None:
        if type(seed) is not str:
            raise ValueError("seed must be an integer string or null")
        try:
            if str(int(seed)) != seed:
                raise ValueError
        except ValueError:
            raise ValueError("seed must be an integer string or null") from None
    if type(data["last_values"]) is not dict:
        raise ValueError("last_values must be an object")
    output = data["output"]
    if (type(output) is not dict or set(output) != {"encoding", "value"}
            or output["encoding"] not in ("json", "custom")):
        raise ValueError("invalid output encoding")
    run = data["run"]
    if run is None:
        if data["last_values"] or output != {"encoding": "json", "value": None}:
            raise ValueError("an uninitialized node cannot hold observations or output")
    elif type(run) is not dict:
        raise ValueError("run must be an upstream checkpoint or null")
    else:
        t = run.get("t")
        if type(t) is not int or t < 0:
            raise ValueError("run.t must be a non-negative integer")
        provenance = run.get("provenance")
        if type(provenance) is not dict:
            raise ValueError("run.provenance must be an object")
        if provenance.get("seed") != seed:
            raise ValueError("node seed does not match upstream provenance")
        if t == 0 and (data["last_values"] or output != {"encoding": "json", "value": None}):
            raise ValueError("a zero-step node cannot hold observations or output")


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
