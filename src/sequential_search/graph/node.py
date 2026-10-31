"""A graph node is an experiment (ADR-001). No statistics in this module.

Runtime-checked invariants (ADR-003, layer 1):
  N1  step() returns a new Observation; the node state is an immutable value and
      a step never mutates its arguments -- transactionality is inherited from
      sequential-analysis' Procedure.
  N2  cost() >= 0 and finite. The cost of an observation may differ per level
      (case 5: a thin slice is more expensive than an averaged one), so it is a
      function of state rather than a constant on the edge.
  N3  canonical_key() is defined for every visited state: two nodes with the
      same key are the same experiment (invariant 5, no double counting). For a
      pure tree the key is unique by construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class Observation:
    """One observation of an experiment: tick + named values.

    Semantically identical to the input mapping of `Procedure.step` in
    sequential-analysis (`{'x': ...}`), so the stats-layer adapter does not
    transform data, it only routes it.
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
    """An experiment producing a stream of observations.

    It is NOT: data, a hypothesis, or an agent's "score" (ADR-001).
    """

    name: str

    def step(self) -> Observation:
        """Take one observation. Idempotence is not required, purity is."""
        ...

    def state(self) -> Any:
        """Current node state as an immutable value (for checkpointing)."""
        ...

    def cost(self) -> float:
        """Cost of the NEXT step (N2)."""
        ...

    def canonical_key(self) -> str:
        """Canonical-form key of the state (N3)."""
        ...

    def is_terminal(self) -> bool:
        """Absorbing state: further steps are forbidden."""
        ...


def check_node(node: Node) -> None:
    """Check invariants N1-N3 against the current node state. Raises ValueError."""
    key = node.canonical_key()
    if not isinstance(key, str) or not key:
        raise ValueError(f"node '{node.name}': canonical_key must be non-empty str")
    c = node.cost()
    if not (isinstance(c, (int, float)) and c >= 0):
        raise ValueError(f"node '{node.name}': cost must be a non-negative number, got {c!r}")
