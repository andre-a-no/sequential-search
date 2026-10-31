"""Degenerate anchor (README invariant 2, ADR-003 corollary 1).

Specification: a single-edge graph root->leaf with an SPRT node must produce
llr/decision values that match SEQUENTIALLY with a standalone run of the same
SPRT from sequential-analysis on the same data and the same seed.

This test is not a check of the traversal implementation (there is none yet); it
checks that the ProcedureNode adapter introduces no distortion. It is green
BEFORE traversal exists.
"""
from __future__ import annotations

import math

import pytest

# The degenerate anchor needs the [full] extra; its absence is a supported
# configuration (ADR-003), so it must skip rather than error. importorskip does
# not catch ImportError raised from find_spec, hence the explicit try/except.
try:
    from sequential_analysis import Run  # noqa: E402
    from sequential_analysis.procedures import Gaussian, SPRT  # noqa: E402
except ImportError as exc:  # pragma: no cover - exercised only without [full]
    pytest.skip(f"requires the [full] extra ({exc})", allow_module_level=True)

from sequential_search.graph.edge import Decision, threshold_rule  # noqa: E402
from sequential_search.stats.procedure import ProcedureNode, wald_thresholds  # noqa: E402

DATA = [0.1, 0.9, 1.2, 0.7, 1.5, 1.1, 0.8, 1.9]


def make_sprt() -> SPRT:
    return SPRT(Gaussian(sigma=1.0), theta0=0.0, theta1=1.0, alpha=0.05, beta=0.1)


def test_wald_thresholds_match_upstream():
    """Kernel boundaries (in e-currency) == exp of upstream boundaries (in log LR)."""
    proc = make_sprt()
    upper_e, lower_e = wald_thresholds(proc.alpha, proc.beta)
    assert math.isclose(upper_e, math.exp(proc.upper), rel_tol=1e-12)
    assert math.isclose(lower_e, math.exp(proc.lower), rel_tol=1e-12)


def test_llr_sequence_matches_standalone_run():
    """Step-by-step agreement of llr and accumulated evidence."""
    standalone = Run(make_sprt())
    standalone.start()

    node = ProcedureNode("root", make_sprt)
    rule = threshold_rule(*wald_thresholds(0.05, 0.1))

    for i, x in enumerate(DATA, start=1):
        ev = standalone.step({"x": x})
        evidence = node.feed({"x": x})

        assert evidence.n == i
        assert math.isclose(ev.output.llr, evidence.stat.llr, rel_tol=0.0, abs_tol=0.0), \
            f"llr diverged at step {i}"

        # the edge's decision (on e-value) == the procedure's decision (on log LR)
        ours = rule.decide(evidence)
        theirs = ev.output.decision
        if theirs is None:
            assert ours is Decision.PENDING, f"step {i}: expected pending"
        elif theirs == "reject_h0":
            assert ours is Decision.ACCEPT, f"step {i}: reject_h0 must be accept(H1)"
        else:
            assert ours is Decision.REJECT, f"step {i}: accept_h0 must be reject"


def test_terminal_agreement():
    """The stopping moment agrees down to the exact index."""
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
    assert stop_standalone == stop_ours == 8  # from the exploratory run: terminal at t=8


def test_checkpoint_roundtrip_is_compatible():
    """Node state is serialisable through the upstream checkpoint and resumable."""
    node = ProcedureNode("root", make_sprt)
    for x in DATA[:5]:
        node.feed({"x": x})
    cp = node._ensure_run().checkpoint()          # upstream format, not our own envelope
    assert cp["format"] and cp["state"] is not None

    resumed = Run.restore(make_sprt(), cp)
    resumed.start()   # restore returns PAUSED (see the upstream docstring)
    a = Run(make_sprt()); a.start()
    for x in DATA:
        a.step({"x": x})
    for x in DATA[5:]:
        resumed.step({"x": x})
    assert math.isclose(resumed.state.llr, a.state.llr, rel_tol=1e-12)
