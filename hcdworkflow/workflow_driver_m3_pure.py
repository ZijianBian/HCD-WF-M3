#!/usr/bin/env python
"""Drive native MUSCLE3 physics actors through the full workflow time loop.

One macro reuse contains all time slices, exchanging IDSs with wired actors.
Zero-power IC slices bypass Cyrano/FoPla: FoPla otherwise renormalizes its
output to the XML target power even when the launched waveform is off.

Launch with: muscle_manager --start-all path/to/pure_case.ymmsl
"""

import os
import sys
import math
from contextlib import ExitStack
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import numpy as np

from libmuscle import Instance, Message, InstanceFlags
from ymmsl import Operator

# Reuse DB layer and IDS utilities from workflow_driver
from workflow.workflow_driver import (
    setup_databases,
    get_ids_slices,
    store_ids_slices,
    resolve_time_range,
)
from workflow.ids_prep import _create_ids


# =============================================================================
# Port registry — one entry per actor
# Each actor has:
#   send: ports driver sends on (O_I)
#   recv: ports driver receives on (S)
# =============================================================================

ACTOR_PORTS = {
    "torbeam": {
        "send": ["equilibrium_out", "core_profiles_out", "ec_launchers_out"],
        "recv": ["waves_in"],
    },
    "cyrano": {
        "send": [
            "equilibrium_out_ic",
            "core_profiles_out_ic",
            "ic_antennas_out",
            "waves_out_to_cyrano",
            "distributions_out_ic",
            "distribution_sources_out_ic",
            "core_sources_out_ic",
            "nbi_out_ic",
        ],
        "recv": ["waves_ic_in"],
    },
    "fopla": {
        "send": [
            "equilibrium_out_fp",
            "core_profiles_out_fp",
            "ic_antennas_out_fp",
            "waves_out_to_fopla",
            "distributions_out_fp",
            "distribution_sources_out_fp",
            "nbi_out_fp",
        ],
        "recv": ["distributions_in"],
    },
    "rabbit": {
        "send": [
            "core_profiles_out_rabbit",
            "equilibrium_out_rabbit",
            "nbi_out_rabbit",
            "wall_out_rabbit",
            "workflow_out_rabbit",
        ],
        "recv": ["distribution_sources_rabbit_in", "distributions_rabbit_in"],
    },
    "merge_waves": {
        "send": ["waves_ec_out", "waves_ic_out"],
        "recv": ["waves_merged_in"],
    },
    "hcd2core_sources": {
        "send": ["distributions_out_post", "distribution_sources_out_post", "waves_out_post", "core_profiles_out_post"],
        "recv": ["core_sources_in"],
    },
}

POWER_EPS_W = 1.0e-6
M3_TIME_TOLERANCE = 1.0e-9


def _validate_parallel_ec_ic(active_actors, cyrano_parameters):
    """Admit only the independent EC/IC topology audited for native CYRANO.

    Cyrano_imas.f reads its coupling/waves input only for Ntor=0,
    frequency=0, or total_power=0. Never silently remove those dependencies.
    Coupled fast-particle topologies are deliberately outside this first opt-in.
    """
    allowed = {"torbeam", "cyrano", "merge_waves", "hcd2core_sources"}
    if not {"torbeam", "cyrano"} <= active_actors or not active_actors <= allowed:
        raise ValueError("Parallel EC/IC requires Torbeam + Cyrano without Rabbit/FoPla")
    root = ET.parse(cyrano_parameters).getroot()

    def number(tag):
        nodes = root.findall(".//" + tag)
        if len(nodes) != 1 or nodes[0].text is None:
            raise ValueError(f"Parallel EC/IC requires one explicit CYRANO {tag}")
        value = float(nodes[0].text)
        if not np.isfinite(value):
            raise ValueError(f"Non-finite CYRANO {tag}")
        return value

    if number("Ntor") == 0 or number("frequency") <= 0:
        raise ValueError("Parallel EC/IC requires explicit nonzero Ntor and positive frequency")
    power = number("total_power")
    if not (power == 1 or power > 2):
        raise ValueError("Parallel EC/IC requires antenna power (1) or explicit power (>2)")
    if any(number(tag) != 0 for tag in ("include_nbi", "include_fasticrh", "include_alphas")):
        raise ValueError("Parallel EC/IC currently requires fast-particle coupling disabled")


def _run_ec_ic(instance, active_actors, eq, cp, ec, ic, cs, dis, dsr, nbi, timenow, t_next, ic_active, parallel=False):
    """Dispatch both native processes before receiving in the opt-in schedule.

    All Instance calls stay on one Python thread. Native actor processes do the
    concurrent work. The serial schedule and its EC-to-IC input are unchanged.
    """
    waves_ec = _empty("waves")
    waves_ic = _empty("waves")
    if "torbeam" in active_actors:
        _send(instance, "equilibrium_out", eq, timenow, t_next)
        _send(instance, "core_profiles_out", cp, timenow, t_next)
        _send(instance, "ec_launchers_out", ec, timenow, t_next)
        if not parallel:
            waves_ec = _recv(instance, "waves_in", "waves", timenow)
    if "cyrano" in active_actors and ic_active:
        # In parallel mode this is an empty placeholder, admitted by the XML
        # dependency guard. EC wave outputs are merged only after both finish.
        for port, ids_obj in (
            ("equilibrium_out_ic", eq),
            ("core_profiles_out_ic", cp),
            ("ic_antennas_out", ic),
            ("waves_out_to_cyrano", waves_ec),
            ("distributions_out_ic", dis),
            ("distribution_sources_out_ic", dsr),
            ("core_sources_out_ic", cs),
            ("nbi_out_ic", nbi),
        ):
            _send(instance, port, ids_obj, timenow, t_next)
        if not parallel:
            waves_ic = _recv(instance, "waves_ic_in", "waves", timenow)
    elif "cyrano" in active_actors:
        print("[driver] Skipping Cyrano because IC launched power is zero", flush=True)
    if parallel:
        if "torbeam" in active_actors:
            waves_ec = _recv(instance, "waves_in", "waves", timenow)
        if "cyrano" in active_actors and ic_active:
            waves_ic = _recv(instance, "waves_ic_in", "waves", timenow)
    return waves_ec, waves_ic


# =============================================================================
# Power-gating helpers
# =============================================================================


def _ec_total_power(ec_launchers_ids) -> float:
    """Sum launched EC power [W] across all beams."""
    if ec_launchers_ids is None:
        return 0.0
    try:
        total = 0.0
        for beam in ec_launchers_ids.beam:
            if hasattr(beam.power_launched, "data") and len(beam.power_launched.data) > 0:
                total += float(beam.power_launched.data[0])
            elif hasattr(beam, "power_launched") and beam.power_launched.has_value:
                total += float(np.asarray(beam.power_launched)[0])
        if not math.isfinite(total):
            raise ValueError("EC launched power must be finite")
        return total
    except (AttributeError, TypeError, ValueError, IndexError) as error:
        raise ValueError("Invalid EC launched-power waveform") from error


def _ic_total_power(ic_antennas_ids) -> float:
    """Sum launched IC power [W] across all antennas."""
    if ic_antennas_ids is None:
        return 0.0
    try:
        total = 0.0
        for antenna in ic_antennas_ids.antenna:
            pl = antenna.power_launched
            if hasattr(pl, "data") and len(pl.data) > 0:
                total += float(pl.data[0])
        if not math.isfinite(total):
            raise ValueError("IC launched power must be finite")
        return total
    except (AttributeError, TypeError, ValueError, IndexError) as error:
        raise ValueError("Invalid IC launched-power waveform") from error


# =============================================================================
# M3 send / recv helpers
# =============================================================================


def _send(instance, port_name, ids_obj, timenow, t_next):
    """Serialize and send an IDS on a port."""
    try:
        data = ids_obj.serialize()
    except Exception as error:
        raise RuntimeError(f"Could not serialize IDS for {port_name}") from error
    print(f"  -> {port_name} ({len(data)} bytes)", flush=True)
    instance.send(port_name, Message(timenow, t_next, data=data))


def _recv(instance, port_name, ids_name, timenow=None) -> object:
    """Receive and deserialize an IDS from a port."""
    print(f"  <- waiting {port_name}...", flush=True)
    msg = instance.receive(port_name)
    if not math.isfinite(msg.timestamp):
        raise RuntimeError(f"Non-finite result timestamp on {port_name}")
    if timenow is not None and not math.isclose(msg.timestamp, timenow, rel_tol=0.0, abs_tol=M3_TIME_TOLERANCE):
        raise RuntimeError(f"Result timestamp on {port_name} is {msg.timestamp:.17g}, " f"expected {timenow:.17g}")
    ids_obj = _create_ids(ids_name)
    if msg.data and len(msg.data) > 0:
        try:
            ids_obj.deserialize(msg.data)
            if hasattr(ids_obj, "time"):
                ids_obj.time = np.array([timenow if timenow is not None else msg.timestamp])
        except Exception as error:
            raise RuntimeError(f"Could not deserialize IDS from {port_name}") from error
    print(f"  <- {port_name} received (msg_t={msg.timestamp:.4f})", flush=True)
    return ids_obj


def _empty(ids_name) -> object:
    """Create a serializable empty IDS placeholder."""
    ids_obj = _create_ids(ids_name)
    ids_obj.ids_properties.homogeneous_time = 0
    return ids_obj


def _prepare_actor_input(ids_name, ids_obj, reference_ids, timenow):
    """Match WorkflowExecutor's empty-IDS compatibility before actor calls."""
    try:
        object.__setattr__(ids_obj, "__name__", ids_name)
    except Exception:
        pass

    try:
        if ids_obj.ids_properties.homogeneous_time < 1:
            ids_obj.ids_properties.homogeneous_time = 1
            if hasattr(ids_obj, "time"):
                if hasattr(reference_ids, "time") and len(reference_ids.time) > 0:
                    ids_obj.time = np.array(reference_ids.time, copy=True)
                else:
                    ids_obj.time = np.array([timenow])
    except (AttributeError, TypeError, ValueError) as error:
        raise RuntimeError(f"Could not prepare {ids_name} for actor input") from error

    return ids_obj


def _create_rabbit_workflow(timenow, dt):
    """Build the minimal workflow IDS contract consumed by Rabbit."""
    workflow = _empty("workflow")
    workflow.ids_properties.homogeneous_time = 1
    workflow.time = np.array([timenow])
    workflow.time_loop.component.resize(1)
    workflow.time_loop.component[0].name = "RABBIT"
    workflow.time_loop.workflow_cycle.resize(1)
    workflow.time_loop.workflow_cycle[0].component.resize(1)
    component = workflow.time_loop.workflow_cycle[0].component[0]
    try:
        component.time_interval_request = dt
    except Exception:
        component.time_interval = dt
    return workflow


def _validate_rabbit_configuration(active_actors, param_process):
    """Require the static topology and nbi_fp=1 selection to agree."""
    connected = "rabbit" in active_actors
    selected = param_process.get("nbi_fp", 0) == 1
    if connected != selected:
        raise RuntimeError(
            "Pure M3 Rabbit requires both a connected rabbit component and " "nbi_fp=1 in input_workflow.xml"
        )
    if connected and "fopla" in active_actors:
        raise RuntimeError("Pure M3 does not yet merge Rabbit and FoPla distributions; " "use the no-FoPla topology")
    return connected


def _run_rabbit(instance, core_profiles, equilibrium, nbi, wall, timenow, t_next, dt):
    """Advance stateful Rabbit once, including zero-NBI-power slices."""
    try:
        n_units = len(nbi.unit)
    except (AttributeError, TypeError) as exc:
        raise ValueError("Rabbit requires a populated nbi IDS") from exc
    if n_units == 0:
        raise ValueError("Rabbit requires a populated nbi IDS; nbi.unit is empty")

    rabbit_workflow = _create_rabbit_workflow(timenow, dt)
    _send(instance, "wall_out_rabbit", wall, timenow, t_next)
    _send(instance, "core_profiles_out_rabbit", core_profiles, timenow, t_next)
    _send(instance, "equilibrium_out_rabbit", equilibrium, timenow, t_next)
    _send(instance, "nbi_out_rabbit", nbi, timenow, t_next)
    _send(instance, "workflow_out_rabbit", rabbit_workflow, timenow, t_next)

    # Rabbit sends distribution_sources before distributions.
    distribution_sources = _recv(instance, "distribution_sources_rabbit_in", "distribution_sources", timenow)
    distributions = _recv(instance, "distributions_rabbit_in", "distributions", timenow)
    return distributions, distribution_sources


# =============================================================================
# Main driver
# =============================================================================


def main():
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    if len(sys.argv) < 2:
        print("Usage: python workflow_driver_m3_pure.py <config_folder_path>")
        sys.exit(1)

    config_path = os.path.abspath(sys.argv[1])
    print("[driver] Pure M3 driver starting", flush=True)
    print(f"[driver] Config: {config_path}", flush=True)

    # --- Create MUSCLE3 Instance ---
    # Collect all send/recv ports from the registry.
    # Only ports that are actually wired in the ymmsl will be connected;
    # driver checks is_connected() before using each port.
    all_send = []
    all_recv = []
    for actor_info in ACTOR_PORTS.values():
        all_send.extend(actor_info["send"])
        all_recv.extend(actor_info["recv"])

    ports = {
        Operator.O_I: all_send,
        Operator.S: all_recv,
    }
    instance = Instance(ports, InstanceFlags.SKIP_MMSF_SEQUENCE_CHECKS)
    print("[driver] M3 instance created", flush=True)

    # --- Determine which actors are actually wired ---
    connected_send = {p for p in all_send if instance.is_connected(p)}

    active_actors = {actor for actor, info in ACTOR_PORTS.items() if any(p in connected_send for p in info["send"])}
    print(f"[driver] Active actors: {sorted(active_actors)}", flush=True)
    if "fopla" in active_actors and "cyrano" not in active_actors:
        raise RuntimeError("Pure M3 FoPla requires a connected Cyrano actor")

    # --- Database setup (reuse workflow_driver layer) ---
    (
        inputDb,
        outputDb,
        machineDb,
        inputIds,
        inputMds,
        wf_parameters,
        param_process,
    ) = setup_databases(config_path)

    with ExitStack() as cleanup:
        for database in (inputDb, outputDb, machineDb):
            if database is not None:
                cleanup.callback(database.close)

        rabbit_enabled = _validate_rabbit_configuration(active_actors, param_process)

        # --- Time range ---
        # Reuse the parameters already read by setup_databases, without loading iWrap actors.
        workflow_config = SimpleNamespace(
            workflowData=SimpleNamespace(
                tbegin=float(wf_parameters["tbegin"][0]),
                tend=float(wf_parameters["tend"][0]),
                dt_required=float(wf_parameters["dt_required"][0]),
                one_time_slice=int(wf_parameters["one_time_slice"][0]),
            )
        )
        tbegin, tend, dt, nsteps, _ = resolve_time_range(workflow_config, inputDb)
        print(f"[driver] Time range: {tbegin} → {tend}, dt={dt}, steps={nsteps}", flush=True)

        # --- Main loop ---
        timenow = tbegin
        step = 0

        while instance.reuse_instance():
            try:
                parallel_ec_ic = instance.get_setting("pure_parallel_ec_ic", "bool")
            except KeyError:
                parallel_ec_ic = False
            if parallel_ec_ic:
                cyrano_parameters = instance.get_setting("cyrano.code_parameters", "str")
                _validate_parallel_ec_ic(active_actors, cyrano_parameters)
            print(f'[driver] EC/IC schedule: {"parallel" if parallel_ec_ic else "serial"}', flush=True)
            while timenow < tend:
                step += 1
                t_next = timenow + dt if timenow + dt < tend else None
                print(f"\n{'='*60}", flush=True)
                print(f"[driver] Step {step}/{nsteps}, t={timenow:.4f}", flush=True)

                # --- Read IDS from DB ---
                ids_slices = get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow)
                if ids_slices is None:
                    raise RuntimeError(f"Failed to read IDS at t={timenow}")

                actor_inputs = {
                    name: ids_slices[name] if name in ids_slices else _empty(name)
                    for name in (
                        "equilibrium",
                        "core_profiles",
                        "ec_launchers",
                        "ic_antennas",
                        "core_sources",
                        "distributions",
                        "distribution_sources",
                        "nbi",
                        "wall",
                    )
                }
                eq, cp, ec, ic, cs, dis, dsr, nbi, wall = actor_inputs.values()
                for ids_name, ids_obj in actor_inputs.items():
                    _prepare_actor_input(ids_name, ids_obj, cp, timenow)

                output_ids = {}

                # ----------------------------------------------------------------
                # EC branch — torbeam
                # ----------------------------------------------------------------
                ec_power = _ec_total_power(ec) if "torbeam" in active_actors else 0.0
                ec_active = "torbeam" in active_actors and ec_power > POWER_EPS_W
                print(f"[driver] EC power = {ec_power/1e6:.3f} MW", flush=True)

                # Keep the IC inputs at their pre-Rabbit values.  This matches the
                # Legacy/Hybrid default actor order: EC -> IC -> merge -> NBI.
                distributions = dis
                distribution_sources = dsr

                # ----------------------------------------------------------------
                # IC branch — cyrano  (only if wired)
                # ----------------------------------------------------------------
                ic_power = _ic_total_power(ic) if "cyrano" in active_actors else 0.0
                ic_active = "cyrano" in active_actors and abs(ic_power) > POWER_EPS_W
                print(f"[driver] IC power = {ic_power/1e6:.3f} MW", flush=True)

                waves_ec, waves_ic = _run_ec_ic(
                    instance,
                    active_actors,
                    eq,
                    cp,
                    ec,
                    ic,
                    cs,
                    distributions,
                    distribution_sources,
                    nbi,
                    timenow,
                    t_next,
                    ic_active,
                    parallel=parallel_ec_ic,
                )

                # ----------------------------------------------------------------
                # Merge waves  (only if wired)
                # ----------------------------------------------------------------
                if "merge_waves" in active_actors and ec_active and ic_active:
                    _send(instance, "waves_ec_out", waves_ec, timenow, t_next)
                    _send(instance, "waves_ic_out", waves_ic, timenow, t_next)
                    waves = _recv(instance, "waves_merged_in", "waves", timenow)
                elif ic_active and not ec_active:
                    if "merge_waves" in active_actors:
                        print("[driver] Skipping merge_waves because EC launched power is zero", flush=True)
                    waves = waves_ic
                else:
                    if "merge_waves" in active_actors and not ic_active:
                        print("[driver] Skipping merge_waves because IC launched power is zero", flush=True)
                    waves = waves_ec

                output_ids["waves"] = waves

                # ----------------------------------------------------------------
                # FP branch — fopla  (only if wired)
                # ----------------------------------------------------------------
                if "fopla" in active_actors and ic_active:
                    _send(instance, "equilibrium_out_fp", eq, timenow, t_next)
                    _send(instance, "core_profiles_out_fp", cp, timenow, t_next)
                    _send(instance, "ic_antennas_out_fp", ic, timenow, t_next)
                    # FoPla is the IC Fokker-Planck actor; feeding merged EC+IC
                    # waves can make it pick the EC wave first and crash in its
                    # RF interpolation. Keep merged waves for downstream storage
                    # and hcd2core_sources, but feed FoPla the IC wave branch.
                    _send(instance, "waves_out_to_fopla", waves_ic, timenow, t_next)
                    _send(instance, "distributions_out_fp", distributions, timenow, t_next)
                    _send(instance, "distribution_sources_out_fp", distribution_sources, timenow, t_next)
                    _send(instance, "nbi_out_fp", nbi, timenow, t_next)
                    distributions = _recv(instance, "distributions_in", "distributions", timenow)
                    output_ids["distributions"] = distributions
                else:
                    if "fopla" in active_actors:
                        print("[driver] Skipping FoPla because IC launched power is zero", flush=True)

                # ----------------------------------------------------------------
                # NBI FP branch — Rabbit (stateful; advance on every time slice)
                # Run after the EC/IC wave merge, matching Legacy/Hybrid, and
                # before hcd2core_sources so its outputs feed post-processing.
                # ----------------------------------------------------------------
                if rabbit_enabled:
                    distributions, distribution_sources = _run_rabbit(instance, cp, eq, nbi, wall, timenow, t_next, dt)
                    output_ids["distributions"] = distributions
                    output_ids["distribution_sources"] = distribution_sources

                # ----------------------------------------------------------------
                # Post-processing — hcd2core_sources  (only if wired)
                # ----------------------------------------------------------------
                if "hcd2core_sources" in active_actors:
                    _send(instance, "distributions_out_post", distributions, timenow, t_next)
                    _send(instance, "distribution_sources_out_post", distribution_sources, timenow, t_next)
                    _send(instance, "waves_out_post", waves, timenow, t_next)
                    _send(instance, "core_profiles_out_post", cp, timenow, t_next)
                    core_sources = _recv(instance, "core_sources_in", "core_sources", timenow)
                    output_ids["core_sources"] = core_sources

                # ----------------------------------------------------------------
                # Write results to DB
                # ----------------------------------------------------------------
                store_ids_slices(
                    outputDb,
                    inputMds,
                    ids_slices,
                    output_ids,
                    m3_flag=1,
                    param_process=param_process,
                    timenow=timenow,
                    config_folder_path=config_path,
                )

                timenow += dt

        print(f"[driver] Finished after {step} steps", flush=True)

    print("[driver] Databases closed", flush=True)


if __name__ == "__main__":
    main()
