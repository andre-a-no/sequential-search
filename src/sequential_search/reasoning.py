# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure reference search over finite positive propositional implications.

Rules have AND premises; alternative producers of a fact are OR choices.
The algorithms operate on explicit facts and rules, not tools or statistical
experiments. They make no claim about weighted optimality or general theorem
proving. Resource costs measure search work, separately from returned proof cost.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Literal

Status = Literal["proved", "conditional", "exhausted", "resource_limit"]


def _atom(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("facts, goals, names and contexts must be non-empty strings")


def _atoms(values: frozenset[str]) -> frozenset[str]:
    if isinstance(values, str):
        raise TypeError("a collection of atoms cannot be a string")
    result = frozenset(values)
    for value in result:
        _atom(value)
    return result


@dataclass(frozen=True)
class Rule:
    name: str
    premises: frozenset[str]
    conclusion: str
    cost: float = 1.0

    def __post_init__(self) -> None:
        _atom(self.name)
        _atom(self.conclusion)
        object.__setattr__(self, "premises", _atoms(self.premises))
        if type(self.cost) not in (int, float) or not math.isfinite(self.cost) or self.cost < 0:
            raise ValueError("rule cost must be finite and non-negative")


@dataclass(frozen=True)
class Problem:
    facts: frozenset[str]
    goal: str
    rules: tuple[Rule, ...]
    context: str = "default"

    def __post_init__(self) -> None:
        _atom(self.goal)
        _atom(self.context)
        object.__setattr__(self, "facts", _atoms(self.facts))
        object.__setattr__(self, "rules", tuple(self.rules))
        if any(not isinstance(rule, Rule) for rule in self.rules):
            raise ValueError("rules must contain Rule objects")
        if len({rule.name for rule in self.rules}) != len(self.rules):
            raise ValueError("rule names must be unique within a problem")


@dataclass(frozen=True)
class Proof:
    context: str
    goal: str
    steps: tuple[str, ...] = ()
    assumptions: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _atom(self.context)
        _atom(self.goal)
        if isinstance(self.steps, str):
            raise TypeError("proof steps must be a collection of rule names")
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "assumptions", _atoms(self.assumptions))
        for name in self.steps:
            _atom(name)


@dataclass(frozen=True)
class Result:
    status: Status
    proof: Proof | None
    missing: frozenset[str]
    expansions: int
    cost: float
    proof_cost: float


def verify_proof(problem: Problem, proof: Proof, *, allow_assumptions: bool = False) -> bool:
    """Check rule identities, order, context, AND premises and used assumptions.

    This checks entailment in the caller's explicit rule system, not whether its
    rules correctly model a subject. Unused valid steps are allowed; unused or
    circular assumptions are not. Conditional proofs require explicit opt-in.
    """
    if proof.context != problem.context or proof.goal != problem.goal:
        return False
    if proof.assumptions and not allow_assumptions:
        return False
    if (proof.assumptions & problem.facts or proof.goal in proof.assumptions
            or len(set(proof.steps)) != len(proof.steps)):
        return False
    rules = {rule.name: rule for rule in problem.rules}
    known = set(problem.facts | proof.assumptions)
    producers: dict[str, Rule] = {}
    for name in proof.steps:
        rule = rules.get(name)
        if rule is None or not rule.premises <= known or rule.conclusion in proof.assumptions:
            return False
        producers.setdefault(rule.conclusion, rule)
        known.add(rule.conclusion)
    if proof.goal not in known:
        return False
    needed = [proof.goal]
    seen: set[str] = set()
    used_assumptions: set[str] = set()
    while needed:
        atom = needed.pop()
        if atom in seen or atom in problem.facts:
            continue
        seen.add(atom)
        if atom in proof.assumptions:
            used_assumptions.add(atom)
        elif atom in producers:
            needed.extend(producers[atom].premises)
        else:
            return False
    return used_assumptions == proof.assumptions


@dataclass
class _Budget:
    maximum: int
    max_cost: float
    expansions: int = 0
    cost: float = 0.0
    limited: bool = False

    def consume(self, cost: float) -> bool:
        if self.expansions >= self.maximum or self.cost + cost > self.max_cost:
            self.limited = True
            return False
        self.expansions += 1
        self.cost += cost
        return True


def _budget(max_expansions: int, max_cost: float) -> _Budget:
    if type(max_expansions) is not int or max_expansions < 0:
        raise ValueError("max_expansions must be a non-negative integer")
    if type(max_cost) not in (int, float) or math.isnan(max_cost) or max_cost < 0:
        raise ValueError("max_cost must be non-negative (positive infinity is allowed)")
    return _Budget(max_expansions, max_cost)


def _proof(problem: Problem, selected: dict[str, Rule], assumptions: frozenset[str]) -> Proof | None:
    """Extract a relevant, topologically ordered acyclic proof without recursion."""
    required: dict[str, Rule] = {}
    missing: set[str] = set()
    todo = [problem.goal]
    seen = set()
    while todo:
        atom = todo.pop()
        if atom in seen or atom in problem.facts:
            continue
        seen.add(atom)
        if atom in assumptions:
            missing.add(atom)
        elif atom in selected:
            required[atom] = selected[atom]
            todo.extend(sorted(selected[atom].premises))
        else:
            return None
    known = problem.facts | assumptions
    dependencies = {atom: len(rule.premises - known) for atom, rule in required.items()}
    dependents: dict[str, list[str]] = {}
    for atom, rule in required.items():
        for premise in sorted(rule.premises - known):
            dependents.setdefault(premise, []).append(atom)
    ready = deque(atom for atom, count in dependencies.items() if count == 0)
    steps = []
    while ready:
        atom = ready.popleft()
        steps.append(required[atom].name)
        for target in dependents.get(atom, ()):
            dependencies[target] -= 1
            if dependencies[target] == 0:
                ready.append(target)
    if len(steps) != len(required) or (missing and not steps):
        return None
    proof = Proof(problem.context, problem.goal, tuple(steps), frozenset(missing))
    return proof if verify_proof(problem, proof, allow_assumptions=True) else None


def _result(problem: Problem, status: Status, proof: Proof | None, budget: _Budget) -> Result:
    by_name = {rule.name: rule for rule in problem.rules}
    return Result(status, proof, proof.assumptions if proof else frozenset({problem.goal}),
                  budget.expansions, budget.cost,
                  sum(by_name[name].cost for name in proof.steps) if proof else 0.0)


def _forward(problem: Problem, budget: _Budget, limit: int | None = None) -> dict[str, Rule]:
    known = set(problem.facts)
    selected: dict[str, Rule] = {}
    examined = 0
    if problem.goal in known:
        return selected
    while True:
        progress = False
        for rule in problem.rules:
            if rule.conclusion in known:
                continue
            if limit is not None and examined >= limit:
                return selected
            enabled = rule.premises <= known
            if not budget.consume(rule.cost if enabled else 0.0):
                continue
            examined += 1
            if enabled:
                known.add(rule.conclusion)
                selected[rule.conclusion] = rule
                progress = True
                if problem.goal in known:
                    return selected
        if not progress:
            return selected


def solve_forward(problem: Problem, *, max_expansions: int = 10_000,
                  max_cost: float = math.inf) -> Result:
    """Saturate facts in declared rule order; no cheapest-proof claim.

    One expansion is one rule applicability check. Cost is charged only when a
    new fact is derived, including facts unused in the eventual proof. Failed
    checks still consume expansion budget. Limits describe this algorithm's work.
    """
    budget = _budget(max_expansions, max_cost)
    selected = _forward(problem, budget)
    proof = _proof(problem, selected, frozenset())
    status: Status = "proved" if proof else "resource_limit" if budget.limited else "exhausted"
    return _result(problem, status, proof, budget)


@dataclass(frozen=True)
class _Candidate:
    pending: frozenset[str]
    selected: tuple[Rule, ...] = ()
    missing: frozenset[str] = frozenset()


def _backward(problem: Problem, budget: _Budget) -> tuple[Status, Proof | None]:
    producers: dict[str, list[Rule]] = {}
    for rule in problem.rules:
        producers.setdefault(rule.conclusion, []).append(rule)
    queue = deque([_Candidate(frozenset({problem.goal}))])
    visited = set()
    best: Proof | None = None
    by_name = {rule.name: rule for rule in problem.rules}

    def score(proof: Proof) -> tuple:
        return (len(proof.assumptions), sum(by_name[name].cost for name in proof.steps),
                tuple(sorted(proof.assumptions)), proof.steps)

    while queue:
        current = queue.popleft()
        selected = {rule.conclusion: rule for rule in current.selected}
        pending = current.pending - problem.facts - frozenset(selected) - current.missing
        identity = (pending, frozenset(rule.name for rule in current.selected), current.missing)
        if identity in visited:
            continue
        visited.add(identity)
        if not pending:
            proof = _proof(problem, selected, current.missing)
            if proof is not None:
                if not proof.assumptions:
                    return "proved", proof
                if best is None or score(proof) < score(best):
                    best = proof
            continue
        atom = min(pending)
        rest = pending - {atom}
        options = producers.get(atom, ())
        if not options:
            if budget.consume(0.0):
                queue.append(_Candidate(rest, current.selected, current.missing | {atom}))
        else:
            for rule in options:
                if budget.consume(rule.cost):
                    queue.append(_Candidate(rest | rule.premises, (*current.selected, rule),
                                            current.missing))
    if budget.limited:
        return "resource_limit", best
    return ("conditional", best) if best else ("exhausted", None)


def solve_backward(problem: Problem, *, max_expansions: int = 10_000,
                   max_cost: float = math.inf) -> Result:
    """Search AND obligations/OR rules, returning checked missing-premise proofs.

    One expansion chooses one producer rule or records an unproduced leaf.
    Rule cost is charged for every explored choice, even a discarded branch.
    Cyclic support is rejected. Missing assumptions are unproduced leaves only;
    arbitrary intermediate conclusions are not assumed to break cycles.
    """
    budget = _budget(max_expansions, max_cost)
    status, proof = _backward(problem, budget)
    return _result(problem, status, proof, budget)


def solve_bidirectional(problem: Problem, *, max_expansions: int = 10_000,
                        max_cost: float = math.inf, forward_steps: int = 1) -> Result:
    """Build a bounded forward prefix, then connect backward obligations to it.

    Both phases share one work budget. Forward-derived facts become checked cut
    points; the returned proof is rebuilt and validated against original facts
    and context. This is a finite reference composition, not balanced optimal
    bidirectional search. forward_steps limits applicability checks in the prefix.
    """
    if type(forward_steps) is not int or forward_steps < 0:
        raise ValueError("forward_steps must be a non-negative integer")
    budget = _budget(max_expansions, max_cost)
    forward = _forward(problem, budget, limit=forward_steps)
    proof = _proof(problem, forward, frozenset())
    if proof is not None:
        return _result(problem, "proved", proof, budget)
    extended = Problem(problem.facts | forward.keys(), problem.goal, problem.rules, problem.context)
    status, backward = _backward(extended, budget)
    if backward is not None:
        by_name = {rule.name: rule for rule in problem.rules}
        selected = {by_name[name].conclusion: by_name[name] for name in backward.steps}
        selected.update(forward)
        proof = _proof(problem, selected, backward.assumptions)
        if proof is None:
            raise RuntimeError("forward/backward connection failed proof validation")
    return _result(problem, status, proof, budget)
