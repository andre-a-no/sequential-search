"""Procedure adapters resume the same experiment, including its statistical RNG."""
from __future__ import annotations

import json
from dataclasses import asdict

import pytest

pytest.importorskip("sequential_analysis", reason="requires the full extra")
from sequential_analysis.errors import IncompatibleCheckpoint
from sequential_analysis.procedures import SPRT, BootstrapParticleFilter, Gaussian
from sequential_analysis.procedures.particle import ParticleOutput
from sequential_analysis.procedures.sprt import SPRTOutput

from sequential_search.core.graph import SearchGraph
from sequential_search.stats.procedure import ProcedureNode

DATA = [0.1, 0.9, 1.2, 0.7, 1.5, 1.1, 0.8, 1.9]


def make_sprt():
    return SPRT(Gaussian(1.0), 0.0, 1.0, alpha=0.05, beta=0.1)


def checkpoint(node):
    # Exercise a real JSON boundary, not merely an in-memory state copy.
    return json.loads(json.dumps(node.checkpoint(encode_output=asdict), allow_nan=False))


def restore(data):
    return ProcedureNode.restore(make_sprt, data, decode_output=lambda value: SPRTOutput(**value))


def test_uninitialized_checkpoint_stays_lazy_and_restores_metadata():
    calls = []

    def factory():
        calls.append(True)
        return make_sprt()

    node = ProcedureNode("trial", factory, cost_per_step=3.5, canonical_key="experiment:1")
    data = node.checkpoint()
    resumed = ProcedureNode.restore(factory, data)
    assert calls == []
    assert data["run"] is None
    assert resumed.name == "trial"
    assert resumed.cost() == 3.5
    assert resumed.canonical_key() == "experiment:1"
    assert resumed.evidence() == node.evidence()
    assert resumed.feed({"x": DATA[0]}) == node.feed({"x": DATA[0]})


def test_initialized_zero_step_checkpoint():
    node = ProcedureNode("trial", make_sprt)
    initial = node.state()
    resumed = ProcedureNode.restore(make_sprt, node.checkpoint())
    assert resumed.state() == initial
    assert resumed.evidence() == node.evidence()
    assert resumed.feed({"x": DATA[0]}) == node.feed({"x": DATA[0]})


def test_pending_resume_matches_uninterrupted_run_step_by_step():
    node = ProcedureNode("trial", make_sprt, cost_per_step=2.0)
    for x in DATA[:5]:
        node.feed({"x": x})
    data = checkpoint(node)
    assert data["run"] == node._ensure_run().checkpoint()
    resumed = restore(data)
    assert resumed.step() == node.step()
    assert resumed.evidence() == node.evidence()
    assert resumed.decision() == node.decision()
    assert resumed.cost() == 2.0
    for x in DATA[5:]:
        assert resumed.feed({"x": x}) == node.feed({"x": x})
        assert resumed.state() == node.state()
        assert resumed.decision() == node.decision()
    assert resumed.is_terminal() and node.is_terminal()
    assert resumed._ensure_run().history_digest == node._ensure_run().history_digest
    assert resumed._ensure_run().run_id == node._ensure_run().run_id


def test_terminal_checkpoint_preserves_evidence_and_decision():
    node = ProcedureNode("trial", make_sprt)
    for x in DATA:
        node.feed({"x": x})
    resumed = restore(checkpoint(node))
    assert resumed.is_terminal()
    assert resumed.state() == node.state()
    assert resumed.evidence() == node.evidence()
    assert resumed.decision() == node.decision()
    assert resumed.step() == node.step()


def test_experiment_key_survives_feed_and_restore():
    node = ProcedureNode("trial", make_sprt)
    graph = SearchGraph()
    key = graph.add_node(node)
    node.feed({"x": DATA[0]})
    resumed = restore(checkpoint(node))
    assert key == node.canonical_key() == resumed.canonical_key() == "trial"
    assert graph.node(key) is node


def test_seeded_particle_filter_continues_bit_for_bit():
    def factory():
        return BootstrapParticleFilter(q=0.1, r=0.5, particles=32)

    node = ProcedureNode("filter", factory, seed=17)
    for y in (0.2, 0.7, -0.1):
        node.feed({"y": y})
    data = checkpoint(node)
    resumed = ProcedureNode.restore(factory, data, decode_output=lambda value: ParticleOutput(**value))
    assert resumed.evidence() == node.evidence()
    for y in (0.6, -0.3, 0.8):
        assert resumed.feed({"y": y}) == node.feed({"y": y})
        assert resumed.state() == node.state()
        assert resumed._ensure_run().rng_state == node._ensure_run().rng_state
    assert resumed._ensure_run().history_digest == node._ensure_run().history_digest


def test_factory_identity_mismatch_is_rejected_by_upstream():
    node = ProcedureNode("trial", make_sprt)
    node.feed({"x": DATA[0]})
    with pytest.raises(IncompatibleCheckpoint, match="procedure mismatch"):
        ProcedureNode.restore(
            lambda: SPRT(Gaussian(1.0), 0.0, 2.0), checkpoint(node),
            decode_output=lambda value: SPRTOutput(**value),
        )


def test_custom_output_requires_explicit_codecs():
    node = ProcedureNode("trial", make_sprt)
    node.feed({"x": DATA[0]})
    with pytest.raises(ValueError, match="encode_output"):
        node.checkpoint()
    with pytest.raises(ValueError, match="decode_output"):
        ProcedureNode.restore(make_sprt, checkpoint(node))


def test_snapshot_detaches_last_observation_and_upstream_state():
    node = ProcedureNode("trial", make_sprt)
    node.feed({"x": DATA[0]})
    data = checkpoint(node)
    data["last_values"]["x"] = 99
    data["run"]["state"]["n"] = 99
    assert node.step().values == {"x": DATA[0]}
    assert node.state().n == 1


@pytest.mark.parametrize("field,value", [
    ("format", "future/99"), ("name", ""), ("cost_per_step", -1),
    ("cost_per_step", float("inf")), ("seed", "not-a-seed"),
    ("last_values", []), ("output", {"encoding": "python", "value": "os.system"}),
])
def test_malformed_adapter_metadata_is_rejected(field, value):
    data = ProcedureNode("trial", make_sprt).checkpoint()
    data[field] = value
    with pytest.raises(ValueError):
        ProcedureNode.restore(make_sprt, data)


def test_seed_cannot_disagree_with_embedded_run():
    node = ProcedureNode("trial", make_sprt)
    node.feed({"x": DATA[0]})
    data = checkpoint(node)
    data["seed"] = "17"
    with pytest.raises(ValueError, match="seed"):
        restore(data)
