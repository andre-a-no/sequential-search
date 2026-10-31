"""Degenerate anchor (инвариант 2 README, ADR-003 следствие 1).

Спецификация: одно-реберный граф root->leaf с SPRT-узлом обязан давать
ПОСЛЕДОВАТЕЛЬНО совпадающие llr/decision с standalone прогоном того же SPRT
из sequential-analysis на тех же данных и том же seed.

Этот тест — не проверка реализации обхода (его ещё нет), а проверка того,
что адаптер ProcedureNode не вносит искажений. Он зелёный ДО traversal.
"""
from __future__ import annotations

import math

import pytest

sa = pytest.importorskip("sequential_analysis", reason="нужен extra [full]")
from sequential_analysis import Run  # noqa: E402
from sequential_analysis.procedures import Gaussian, SPRT  # noqa: E402

from sequential_search.core.edge import Decision, threshold_rule  # noqa: E402
from sequential_search.stats.procedure import ProcedureNode, wald_thresholds  # noqa: E402

DATA = [0.1, 0.9, 1.2, 0.7, 1.5, 1.1, 0.8, 1.9]


def make_sprt() -> SPRT:
    return SPRT(Gaussian(sigma=1.0), theta0=0.0, theta1=1.0, alpha=0.05, beta=0.1)


def test_wald_thresholds_match_upstream():
    """Границы ядра (в e-валюте) == exp-границы upstream (в log LR)."""
    proc = make_sprt()
    upper_e, lower_e = wald_thresholds(proc.alpha, proc.beta)
    assert math.isclose(upper_e, math.exp(proc.upper), rel_tol=1e-12)
    assert math.isclose(lower_e, math.exp(proc.lower), rel_tol=1e-12)


def test_llr_sequence_matches_standalone_run():
    """Пошаговое совпадение llr и накопленных улик."""
    standalone = Run(make_sprt())
    standalone.start()

    node = ProcedureNode("root", make_sprt)
    rule = threshold_rule(*wald_thresholds(0.05, 0.1))

    for i, x in enumerate(DATA, start=1):
        ev = standalone.step({"x": x})
        evidence = node.feed({"x": x})

        assert evidence.n == i
        assert math.isclose(ev.output.llr, evidence.stat.llr, rel_tol=0.0, abs_tol=0.0), \
            f"llr разошёлся на шаге {i}"

        # решение ребра (по e-value) == решение процедуры (по log LR)
        ours = rule.decide(evidence)
        theirs = ev.output.decision
        if theirs is None:
            assert ours is Decision.PENDING, f"шаг {i}: ожидаем pending"
        elif theirs == "reject_h0":
            assert ours is Decision.ACCEPT, f"шаг {i}: reject_h0 должен быть accept(H1)"
        else:
            assert ours is Decision.REJECT, f"шаг {i}: accept_h0 должен быть reject"


def test_terminal_agreement():
    """Момент остановки совпадает ровно до индекса."""
    standalone = Run(make_sprt())
    standalone.start()
    node = ProcedureNode("root", make_sprt)

    stop_standalone = stop_ours = None
    for i, x in enumerate(DATA, start=1):
        ev = standalone.step({"x": x})
        node.feed({"x": x})
        if ev.terminal and stop_standalone is None:
            stop_standalone = i
        if node.is_terminal() and stop_ours is None:
            stop_ours = i
    assert stop_standalone == stop_ours == 8  # из разведочного прогона: терминал на t=8


def test_checkpoint_roundtrip_is_compatible():
    """Состояние узла сериализуемо через upstream-чекпоинт и продолжимо."""
    node = ProcedureNode("root", make_sprt)
    for x in DATA[:5]:
        node.feed({"x": x})
    cp = node._ensure_run().checkpoint()          # формат upstream, не свой envelope
    assert cp["format"] and cp["state"] is not None

    resumed = Run.restore(make_sprt(), cp)
    resumed.start()   # restore возвращает PAUSED (см. докстринг upstream)
    a = Run(make_sprt()); a.start()
    for x in DATA:
        a.step({"x": x})
    for x in DATA[5:]:
        resumed.step({"x": x})
    assert math.isclose(resumed.state.llr, a.state.llr, rel_tol=1e-12)
