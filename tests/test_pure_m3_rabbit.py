from types import SimpleNamespace

import numpy as np
import pytest

from hcdworkflow import workflow_driver_m3_pure as pure


def test_rabbit_registry_declares_five_inputs_and_two_outputs():
    assert pure.ACTOR_PORTS["rabbit"] == {
        "send": [
            "core_profiles_out_rabbit",
            "equilibrium_out_rabbit",
            "nbi_out_rabbit",
            "wall_out_rabbit",
            "workflow_out_rabbit",
        ],
        "recv": [
            "distribution_sources_rabbit_in",
            "distributions_rabbit_in",
        ],
    }


def test_send_ids_name_inference_preserves_underscores():
    ids_obj = SimpleNamespace(metadata=SimpleNamespace(name="core_profiles"))
    assert pure._ids_name_for_send(ids_obj, "core_profiles_out_rabbit") == "core_profiles"

    no_metadata = object()
    assert pure._ids_name_for_send(
        no_metadata, "distribution_sources_out_post"
    ) == "distribution_sources"


def test_rabbit_requires_matching_nbi_fp_selection_and_no_fopla():
    assert pure._validate_rabbit_configuration({"rabbit"}, {"nbi_fp": 1})
    assert not pure._validate_rabbit_configuration(set(), {"nbi_fp": 0})

    with pytest.raises(RuntimeError, match="nbi_fp=1"):
        pure._validate_rabbit_configuration({"rabbit"}, {"nbi_fp": 0})
    with pytest.raises(RuntimeError, match="nbi_fp=1"):
        pure._validate_rabbit_configuration(set(), {"nbi_fp": 1})
    with pytest.raises(RuntimeError, match="does not yet merge"):
        pure._validate_rabbit_configuration(
            {"rabbit", "fopla"}, {"nbi_fp": 1})


def test_rabbit_pure_driver_accepts_legacy_manager_database_setup():
    legacy = tuple(range(7))
    assert pure._unpack_database_setup(legacy) == (*range(5), 6, None, ())


def test_rabbit_workflow_contains_rabbit_component_and_dt():
    workflow = pure._create_rabbit_workflow(80.0, 5.0)

    assert np.asarray(workflow.time).tolist() == [80.0]
    assert str(workflow.time_loop.component[0].name) == "RABBIT"
    component = workflow.time_loop.workflow_cycle[0].component[0]
    interval = (
        component.time_interval_request
        if component.time_interval_request.has_value
        else component.time_interval
    )
    assert float(interval) == pytest.approx(5.0)


def test_rabbit_advances_and_returns_both_outputs_when_nbi_power_is_zero(monkeypatch):
    sent_ports = []
    received_ports = []
    zero_power_nbi = SimpleNamespace(
        unit=[SimpleNamespace(power_launched=SimpleNamespace(data=np.array([0.0])))]
    )

    monkeypatch.setattr(
        pure,
        "_create_rabbit_workflow",
        lambda timenow, dt: SimpleNamespace(timenow=timenow, dt=dt),
    )
    monkeypatch.setattr(
        pure,
        "_send",
        lambda instance, port, ids_obj, timenow, t_next: sent_ports.append(port),
    )

    outputs = {
        "distribution_sources_rabbit_in": object(),
        "distributions_rabbit_in": object(),
    }

    def fake_recv(instance, port, ids_name, timenow):
        received_ports.append(port)
        return outputs[port]

    monkeypatch.setattr(pure, "_recv", fake_recv)

    distributions, distribution_sources = pure._run_rabbit(
        object(), object(), object(), zero_power_nbi, object(), 80.0, 85.0, 5.0)

    assert sent_ports == [
        "wall_out_rabbit",
        "core_profiles_out_rabbit",
        "equilibrium_out_rabbit",
        "nbi_out_rabbit",
        "workflow_out_rabbit",
    ]
    assert received_ports == [
        "distribution_sources_rabbit_in",
        "distributions_rabbit_in",
    ]
    assert distributions is outputs["distributions_rabbit_in"]
    assert distribution_sources is outputs["distribution_sources_rabbit_in"]
