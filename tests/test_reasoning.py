# SPDX-License-Identifier: AGPL-3.0-or-later
"""Finite implication search is checked independently of its selection policy."""
from __future__ import annotations

import itertools
import random
from dataclasses import replace

import pytest

from sequential_search.reasoning import (
    Problem,
    Proof,
    Rule,
    solve_backward,
    solve_bidirectional,
    solve_forward,
    verify_proof,
)

SOLVERS = (solve_forward, solve_backward, solve_bidirectional)


def problem():
    return Problem(frozenset({"given:a", "given:b"}), "goal", (
        Rule("dead-end", frozenset({"unknown"}), "goal"),
        Rule("lemma", frozenset({"given:a"}), "intermediate"),
        Rule("finish", frozenset({"intermediate", "given:b"}), "goal"),
    ), context="geometry/example-v1")


@pytest.mark.parametrize("solve", SOLVERS)
def test_and_premises_or_alternatives_and_validated_provenance(solve):
    p = problem()
    result = solve(p)
    assert result.status == "proved"
    assert result.proof is not None
    assert result.proof.steps == ("lemma", "finish")
    assert result.missing == frozenset()
    assert result.proof_cost == 2.0
    assert verify_proof(p, result.proof)


@pytest.mark.parametrize("solve", SOLVERS)
def test_an_and_transition_cannot_close_only_one_premise(solve):
    p = Problem(frozenset({"a"}), "goal", (Rule("both", frozenset({"a", "b"}), "goal"),))
    result = solve(p)
    assert result.status != "proved"
    if solve is not solve_forward:
        assert result.status == "conditional"
        assert result.missing == frozenset({"b"})
        assert result.proof is not None
        assert not verify_proof(p, result.proof)
        assert verify_proof(p, result.proof, allow_assumptions=True)


@pytest.mark.parametrize("solve", SOLVERS)
def test_initial_goal_needs_no_expansion_or_cost(solve):
    p = Problem(frozenset({"goal"}), "goal", ())
    result = solve(p, max_expansions=0, max_cost=0)
    assert result.status == "proved"
    assert result.expansions == result.cost == result.proof_cost == 0
    assert result.proof == Proof("default", "goal")


@pytest.mark.parametrize("solve", SOLVERS)
def test_cycle_does_not_invent_a_proof_or_a_missing_assumption(solve):
    p = Problem(frozenset(), "a", (
        Rule("a-from-b", frozenset({"b"}), "a"),
        Rule("b-from-a", frozenset({"a"}), "b"),
    ))
    result = solve(p)
    assert result.status == "exhausted"
    assert result.proof is None


@pytest.mark.parametrize("solve", SOLVERS)
def test_cycle_with_an_independent_grounded_alternative(solve):
    p = Problem(frozenset({"given"}), "a", (
        Rule("a-from-b", frozenset({"b"}), "a"),
        Rule("b-from-a", frozenset({"a"}), "b"),
        Rule("grounded", frozenset({"given"}), "b"),
    ))
    result = solve(p)
    assert result.status == "proved"
    assert result.proof is not None
    assert verify_proof(p, result.proof)


@pytest.mark.parametrize("solve", SOLVERS)
@pytest.mark.parametrize("limits", [{"max_expansions": 0}, {"max_cost": 0}])
def test_limit_is_reported_separately_from_exhaustion(solve, limits):
    p = Problem(frozenset({"a"}), "goal", (Rule("derive", frozenset({"a"}), "goal"),))
    limited = solve(p, **limits)
    assert limited.status == "resource_limit"
    assert limited.proof is None
    assert solve(p).status == "proved"
    assert solve(replace(p, rules=())).status == "exhausted"


def test_search_work_cost_is_distinct_from_selected_proof_cost():
    p = Problem(frozenset({"a"}), "goal", (
        Rule("unused", frozenset({"a"}), "irrelevant", cost=100),
        Rule("derive", frozenset({"a"}), "goal", cost=2),
    ))
    result = solve_forward(p)
    assert result.cost == 102
    assert result.proof_cost == 2
    assert result.proof is not None
    assert result.proof.steps == ("derive",)
    cheaper_work = solve_forward(p, max_cost=2)
    assert cheaper_work.status == "proved"
    assert cheaper_work.cost == 2


def test_conditional_alternatives_are_explicit_and_do_not_mask_a_proof():
    p = Problem(frozenset(), "goal", (
        Rule("two-missing", frozenset({"x", "y"}), "goal"),
        Rule("one-missing", frozenset({"z"}), "goal", cost=3),
    ))
    result = solve_backward(p)
    assert result.status == "conditional"
    assert result.missing == frozenset({"z"})
    assert result.proof is not None
    assert verify_proof(p, result.proof, allow_assumptions=True)
    grounded = replace(p, rules=(*p.rules, Rule("axiom", frozenset(), "y"),
                                Rule("known", frozenset(), "x")))
    assert solve_backward(grounded).status == "proved"


@pytest.mark.parametrize("bad", [
    Proof("wrong-context", "goal", ("lemma", "finish")),
    Proof("geometry/example-v1", "other", ("lemma", "finish")),
    Proof("geometry/example-v1", "goal", ("finish", "lemma")),
    Proof("geometry/example-v1", "goal", ("invented-rule",)),
    Proof("geometry/example-v1", "goal", ("lemma", "finish", "finish")),
    Proof("geometry/example-v1", "goal", ("lemma", "finish"), frozenset({"unused"})),
    Proof("geometry/example-v1", "goal", (), frozenset({"goal"})),
])
def test_verifier_rejects_invalid_or_incompatible_connections(bad):
    assert not verify_proof(problem(), bad, allow_assumptions=True)


def test_bidirectional_cut_point_is_replaced_by_forward_provenance():
    p = replace(problem(), rules=problem().rules[1:])
    result = solve_bidirectional(p, forward_steps=1)
    assert result.status == "proved"
    assert result.proof == Proof(p.context, "goal", ("lemma", "finish"))
    assert verify_proof(p, result.proof)
    # An ungrounded intermediate cannot be smuggled into the original problem.
    assert not verify_proof(p, Proof(p.context, "goal", ("finish",)))


@pytest.mark.parametrize("solve", SOLVERS)
def test_deep_chain_uses_no_python_recursion(solve):
    rules = tuple(Rule(f"step:{i}", frozenset({str(i)}), str(i + 1)) for i in range(1200))
    p = Problem(frozenset({"0"}), "1200", rules)
    result = solve(p)
    assert result.status == "proved"
    assert result.proof is not None
    assert len(result.proof.steps) == 1200
    assert verify_proof(p, result.proof)


def test_small_systems_agree_with_independent_truth_table_entailment():
    rng = random.Random(19)
    atoms = ("a", "b", "c", "d")
    for _ in range(50):
        rules = tuple(Rule(f"rule:{i}", frozenset(a for a in atoms if rng.random() < 0.3),
                           rng.choice(atoms)) for i in range(5))
        p = Problem(frozenset(a for a in atoms if rng.random() < 0.2), rng.choice(atoms), rules)
        models = []
        for values in itertools.product((False, True), repeat=len(atoms)):
            true = {atom for atom, value in zip(atoms, values) if value}
            if p.facts <= true and all(not r.premises <= true or r.conclusion in true for r in rules):
                models.append(true)
        entailed = all(p.goal in model for model in models)
        for solve in SOLVERS:
            result = solve(p)
            assert (result.status == "proved") == entailed
            if result.proof is not None:
                assert verify_proof(p, result.proof, allow_assumptions=True)


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf"), True])
def test_invalid_rule_costs(cost):
    with pytest.raises(ValueError):
        Rule("derive", frozenset({"a"}), "b", cost)


@pytest.mark.parametrize("limits", [
    {"max_expansions": -1}, {"max_expansions": True},
    {"max_cost": float("nan")}, {"max_cost": -1},
])
def test_invalid_limits(limits):
    with pytest.raises(ValueError):
        solve_forward(problem(), **limits)


def test_duplicate_rule_names_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        Problem(frozenset(), "a", (Rule("same", frozenset(), "a"), Rule("same", frozenset(), "b")))
