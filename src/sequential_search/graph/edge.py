"""A graph edge is a stopping rule (ADR-001). A boolean predicate is its
degenerate case.

Invariants:
  E1  decide() is pure: the decision depends only on the accumulated evidence
      and the thresholds passed as arguments -- not on traversal order or on the
      policy's history. Otherwise the global guarantee (README invariant 1) is
      unprovable.
  E2  Three outcomes: accept / reject / pending. Pending allows arbitrarily long
      accumulation -- an anytime-valid edge never "times out" (case 6,
      perpetual traversal).
  E3  A classical binary test is an Edge with a single evidence source and two
      non-empty outcomes. Special-casing in code is forbidden: it falls out of
      parameterisation. The specification is fixed by the code in
      tests/test_degenerate_anchor.py (no separate markdown spec file exists;
      see the note in README).
  E4  WITHDRAW exists in the contract but cannot be produced by any built-in
      rule (ADR-005, hole D). The mechanism that produces it is a cost-to-go
      criterion at the traversal/budget level, not a StoppingRule: the decision
      to "stand up" is taken from continuation cost, not from evidence
      strength. Returning WITHDRAW from a rule is a program bug, so
      Edge.decide() intercepts it.
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


#: Terminal edge outcomes. RESUME is not terminal: it returns the edge to
#: PENDING (ADR-006), hence it is absent from this set.
TERMINAL_DECISIONS: frozenset[Decision] = frozenset(
    {Decision.ACCEPT, Decision.REJECT, Decision.WITHDRAW}
)

#: Outcomes under which the alpha share reserved for the edge may be returned
#: to the common pool (ADR-005 corollary 2, ADR-006). REJECT does not return
#: it: a false rejection is precisely the error the budget paid for upfront.
REFUNDABLE_DECISIONS: frozenset[Decision] = frozenset({Decision.WITHDRAW})


class RuleContractError(RuntimeError):
    """A StoppingRule returned an outcome it is forbidden to produce (E4)."""


@dataclass(frozen=True)
class EvidenceState:
    """Evidence accumulated on an edge. Currency: e-value (ADR-003, layer 2).

    `e` >= 1 is read as strength of evidence against the null; `stat` keeps the
    procedure's native quantity (log LR for SPRT, etc.) for compatibility with
    sequential-analysis checkpoints.
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
    """A pure map from evidence to decision (E1).

    Returning WITHDRAW/RESUME is forbidden: the first is produced only by a
    cost-to-go criterion outside the rule, the second only by an external
    resumption event (E4).
    """

    def decide(self, evidence: EvidenceState) -> Decision:
        ...


@dataclass(frozen=True)
class Edge:
    """An edge = (stopping rule, semantic direction label).

    `dependency_scope` is a reserved field (ADR-004, hole A): identifier of the
    environment/source whose observations are correlated. Its semantics is not
    defined yet and it does not affect decisions; it is introduced now so that
    adding budget calibration for dependent checks later does not break the
    contract. An empty string means "independent edge" (current default).
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
                f"edge {self.source}->{self.target}: StoppingRule returned {d.value}; "
                "WITHDRAW is produced by a cost-to-go criterion outside the rule, "
                "RESUME by an external resumption event (invariant E4)"
            )
        return d


def threshold_rule(upper: float, lower: float | None) -> "_ThresholdRule":
    """Canonical rule: e >= upper -> accept, e <= lower -> reject.

    For the degenerate case (SPRT) it is called with
    upper = exp(log((1-beta)/alpha)), lower = exp(log(beta/(1-alpha)))
    -- see the degenerate anchor.
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
