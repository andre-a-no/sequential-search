"""Traversal policy = pure function (frontier x budgets) -> next node.

Definition (ADR-003, layer 4): a policy is *guarantee-invariant* if for any
observation sequence the traversal's error distribution (FWER/FDR, ARL) does
not depend on the choice made by the policy. Formally: an edge decision is a
function only of that edge's accumulated evidence (invariant E1), while the
policy influences merely WHICH evidence has managed to accumulate by the time
the budget stops the traversal.

Corollary: a policy must call `node.feed(values)` and read
`edge.decide(evidence)`, but has no right to produce decisions itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Budgets:
    """Two-dimensional budget (ADR-001): risk and resource are not convertible.

    Both dimensions are *renewable* (ADR-006): WITHDRAW returns to the pool the
    alpha share reserved for a stopped branch together with its cost. The
    return is possible only because alpha is spent as a **reservation** against
    a possible error on that edge rather than as a non-refundable expense; if
    the edge is closed without accept/reject, the reservation was never used.

    Invariant B1 (non-overrun): no operation may spend more than was allocated
    -- otherwise the global guarantee is meaningless.
    Invariant B2 (refund correctness): a refund cannot exceed what was
    previously reserved. Violation is a program bug, not a "better plan".
    """

    alpha_left: float     # free alpha budget (e-value calibration)
    cost_left: float      # free cost (steps, bytes, tokens, seconds)
    #: how much alpha and cost are currently reserved under open edges
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
        """Allocate alpha and cost to an edge/node. Non-overrun is B1."""
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
        """Return unspent allocation to the pool (WITHDRAW semantics). B2-bounded."""
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
        """Return a node key, or None (stop because the budget ran out). Accumulates nothing.

        Stopping via `None` is NOT an inference about the data: it is the end of
        the traversal because the budget is exhausted. Do not confuse with
        WITHDRAW (a decision to abandon a branch while budget remains)
        -- ADR-005/006.
        """
        ...
