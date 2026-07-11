#!/usr/bin/env python
"""
workflow_driver_m3_pure.py — Pure M3 Macro Driver

Pure M3 mode: this driver communicates directly with physics actor
executables (torbeam_m3.exe, cyrano_m3.exe, …) as individual MUSCLE3
micro models. No iWrap wrapper in between.

Contrast with hybrid mode (workflow_driver.py --m3_flag=1):
    hybrid: driver ──► hcd_workflow_m3 (calls actors internally)
    pure:   driver ──► torbeam_m3.exe  (M3 touches actor directly)
            driver ──► cyrano_m3.exe
            driver ──► fopla_m3.exe
            ...

Time control: one macro reuse contains the full time loop; each O_I/S
exchange drives one micro actor reuse.

Actor protocol:
    The driver sends to wired actors when their branch is active. Zero-power
    IC slices bypass Cyrano/FoPla, because FoPla renormalizes to its XML
    target power even when the IC launched waveform is off.

Usage (launched by MUSCLE3 Manager via ymmsl):
    muscle_manager --start-all path/to/pure_case.ymmsl
"""

import os
import sys
import numpy as np

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

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
    'torbeam': {
        'send': ['equilibrium_out', 'core_profiles_out', 'ec_launchers_out'],
        'recv': ['waves_in'],
    },
    'cyrano': {
        'send': ['equilibrium_out_ic', 'core_profiles_out_ic', 'ic_antennas_out',
                 'waves_out_to_cyrano', 'distributions_out_ic',
                 'distribution_sources_out_ic', 'core_sources_out_ic',
                 'nbi_out_ic'],
        'recv': ['waves_ic_in'],
    },
    'fopla': {
        'send': ['equilibrium_out_fp', 'core_profiles_out_fp', 'ic_antennas_out_fp',
                 'waves_out_to_fopla', 'distributions_out_fp',
                 'distribution_sources_out_fp', 'nbi_out_fp'],
        'recv': ['distributions_in'],
    },
    'rabbit': {
        'send': ['core_profiles_out_rabbit', 'equilibrium_out_rabbit',
                 'nbi_out_rabbit', 'wall_out_rabbit', 'workflow_out_rabbit'],
        'recv': ['distribution_sources_rabbit_in', 'distributions_rabbit_in'],
    },
    'merge_waves': {
        'send': ['waves_ec_out', 'waves_ic_out'],
        'recv': ['waves_merged_in'],
    },
    'hcd2core_sources': {
        'send': ['distributions_out_post', 'distribution_sources_out_post',
                 'waves_out_post', 'core_profiles_out_post'],
        'recv': ['core_sources_in'],
    },
}

POWER_EPS_W = 1.0e-6


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
            if hasattr(beam.power_launched, 'data') and len(beam.power_launched.data) > 0:
                total += float(beam.power_launched.data[0])
            elif hasattr(beam, 'power_launched') and beam.power_launched.has_value:
                total += float(np.asarray(beam.power_launched)[0])
        return total
    except Exception:
        return 0.0


def _ic_total_power(ic_antennas_ids) -> float:
    """Sum launched IC power [W] across all antennas."""
    if ic_antennas_ids is None:
        return 0.0
    try:
        total = 0.0
        for antenna in ic_antennas_ids.antenna:
            pl = antenna.power_launched
            if hasattr(pl, 'data') and len(pl.data) > 0:
                total += float(pl.data[0])
        return total
    except Exception:
        return 0.0


# =============================================================================
# M3 send / recv helpers
# =============================================================================

_IDS_NAMES_BY_LENGTH = tuple(sorted((
    'distribution_sources', 'core_profiles', 'core_sources',
    'ec_launchers', 'ic_antennas', 'equilibrium', 'distributions',
    'workflow', 'waves', 'nbi', 'wall',
), key=len, reverse=True))


def _ids_name_for_send(ids_obj, port_name):
    """Resolve the IDS type without truncating names containing underscores."""
    ids_name = getattr(ids_obj, '__name__', None)
    if ids_name:
        return str(ids_name)
    try:
        ids_name = ids_obj.metadata.name
    except Exception:
        ids_name = None
    if ids_name:
        return str(ids_name)
    for candidate in _IDS_NAMES_BY_LENGTH:
        if port_name == f'{candidate}_out' or port_name.startswith(f'{candidate}_'):
            return candidate
    raise ValueError(f"Cannot infer IDS type for send port '{port_name}'")


def _send(instance, port_name, ids_obj, timenow, t_next):
    """Serialize and send an IDS on a port."""
    try:
        data = ids_obj.serialize()
    except Exception as e:
        print(f"  -> WARNING: {port_name} serialization failed ({e}), sending empty", flush=True)
        empty = _create_ids(_ids_name_for_send(ids_obj, port_name))
        empty.ids_properties.homogeneous_time = 0
        try:
            data = empty.serialize()
        except Exception:
            data = b''
    print(f"  -> {port_name} ({len(data)} bytes)", flush=True)
    instance.send(port_name, Message(timenow, t_next, data=data))


def _recv(instance, port_name, ids_name, timenow=None) -> object:
    """Receive and deserialize an IDS from a port."""
    print(f"  <- waiting {port_name}...", flush=True)
    msg = instance.receive(port_name)
    ids_obj = _create_ids(ids_name)
    if msg.data and len(msg.data) > 0:
        try:
            ids_obj.deserialize(msg.data)
            if hasattr(ids_obj, 'time'):
                ids_obj.time = np.array([timenow if timenow is not None else msg.timestamp])
        except Exception as e:
            print(f"  <- WARNING: {port_name} deserialize failed: {e}", flush=True)
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
        object.__setattr__(ids_obj, '__name__', ids_name)
    except Exception:
        pass

    try:
        if ids_obj.ids_properties.homogeneous_time < 1:
            ids_obj.ids_properties.homogeneous_time = 1
            if hasattr(ids_obj, 'time'):
                if hasattr(reference_ids, 'time') and len(reference_ids.time) > 0:
                    ids_obj.time = np.array(reference_ids.time, copy=True)
                else:
                    ids_obj.time = np.array([timenow])
    except Exception as e:
        print(f"  -> WARNING: could not prepare {ids_name} for actor input ({e})", flush=True)

    return ids_obj


def _create_rabbit_workflow(timenow, dt):
    """Build the minimal workflow IDS contract consumed by Rabbit."""
    workflow = _empty('workflow')
    workflow.ids_properties.homogeneous_time = 1
    workflow.time = np.array([timenow])
    workflow.time_loop.component.resize(1)
    workflow.time_loop.component[0].name = 'RABBIT'
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
    connected = 'rabbit' in active_actors
    selected = param_process.get('nbi_fp', 0) == 1
    if connected != selected:
        raise RuntimeError(
            "Pure M3 Rabbit requires both a connected rabbit component and "
            "nbi_fp=1 in input_workflow.xml"
        )
    if connected and 'fopla' in active_actors:
        raise RuntimeError(
            "Pure M3 does not yet merge Rabbit and FoPla distributions; "
            "use the no-FoPla topology"
        )
    return connected


def _run_rabbit(instance, core_profiles, equilibrium, nbi, wall,
                timenow, t_next, dt):
    """Advance stateful Rabbit once, including zero-NBI-power slices."""
    try:
        n_units = len(nbi.unit)
    except (AttributeError, TypeError) as exc:
        raise ValueError("Rabbit requires a populated nbi IDS") from exc
    if n_units == 0:
        raise ValueError("Rabbit requires a populated nbi IDS; nbi.unit is empty")

    rabbit_workflow = _create_rabbit_workflow(timenow, dt)
    _send(instance, 'wall_out_rabbit',          wall,            timenow, t_next)
    _send(instance, 'core_profiles_out_rabbit', core_profiles,   timenow, t_next)
    _send(instance, 'equilibrium_out_rabbit',   equilibrium,     timenow, t_next)
    _send(instance, 'nbi_out_rabbit',           nbi,             timenow, t_next)
    _send(instance, 'workflow_out_rabbit',      rabbit_workflow, timenow, t_next)

    # Rabbit sends distribution_sources before distributions.
    distribution_sources = _recv(
        instance, 'distribution_sources_rabbit_in',
        'distribution_sources', timenow)
    distributions = _recv(
        instance, 'distributions_rabbit_in', 'distributions', timenow)
    return distributions, distribution_sources


# =============================================================================
# Main driver
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python workflow_driver_m3_pure.py <config_folder_path>")
        sys.exit(1)

    config_path = os.path.abspath(sys.argv[1])
    print(f"[driver] Pure M3 driver starting", flush=True)
    print(f"[driver] Config: {config_path}", flush=True)

    # --- Create MUSCLE3 Instance ---
    # Collect all send/recv ports from the registry.
    # Only ports that are actually wired in the ymmsl will be connected;
    # driver checks is_connected() before using each port.
    all_send = []
    all_recv = []
    for actor_info in ACTOR_PORTS.values():
        all_send.extend(actor_info['send'])
        all_recv.extend(actor_info['recv'])

    ports = {
        Operator.O_I: all_send,
        Operator.S:   all_recv,
    }
    instance = Instance(ports, InstanceFlags.SKIP_MMSF_SEQUENCE_CHECKS)
    print(f"[driver] M3 instance created", flush=True)

    # --- Determine which actors are actually wired ---
    connected_send = {p for p in all_send if instance.is_connected(p)}
    connected_recv = {p for p in all_recv if instance.is_connected(p)}

    active_actors = {
        actor for actor, info in ACTOR_PORTS.items()
        if any(p in connected_send for p in info['send'])
    }
    print(f"[driver] Active actors: {sorted(active_actors)}", flush=True)

    # --- Database setup (reuse workflow_driver layer) ---
    inputDb, outputDb, machineDb, inputIds, inputMds, _, param_process = \
        setup_databases(config_path)

    rabbit_enabled = _validate_rabbit_configuration(
        active_actors, param_process)

    # --- Time range ---
    # Read workflow parameters directly from XML — pure M3 mode does not need
    # iWrap actors, so we bypass HCDWorkflow/WorkflowData to avoid importing them.
    from hcdworkflow.workflow_config_reader import WorkflowConfigReader
    wf_xml = os.path.join(config_path, "input_workflow.xml")
    params = WorkflowConfigReader(wf_xml).getWorkflowParameters()

    class _WFStub:
        class workflowData:
            pass
    _stub = _WFStub()
    _stub.workflowData.tbegin = float(params["tbegin"])
    _stub.workflowData.tend = float(params["tend"])
    _stub.workflowData.dt_required = float(params["dt_required"])
    _stub.workflowData.one_time_slice = int(params["one_time_slice"])

    tbegin, tend, dt, nsteps, one_time_slice = resolve_time_range(_stub, inputDb)
    print(f"[driver] Time range: {tbegin} → {tend}, dt={dt}, steps={nsteps}", flush=True)

    # --- Main loop ---
    timenow = tbegin
    step = 0

    while instance.reuse_instance():
        while timenow < tend:
            step += 1
            t_next = timenow + dt if timenow + dt < tend else None
            print(f"\n{'='*60}", flush=True)
            print(f"[driver] Step {step}/{nsteps}, t={timenow:.4f}", flush=True)

            # --- Read IDS from DB ---
            ids_slices = get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow)
            if ids_slices is None:
                print(f"[driver] ERROR: failed to read IDS at t={timenow}", flush=True)
                timenow += dt
                continue

            eq  = ids_slices.get('equilibrium',  _empty('equilibrium'))
            cp  = ids_slices.get('core_profiles', _empty('core_profiles'))
            ec  = ids_slices.get('ec_launchers',  _empty('ec_launchers'))
            ic  = ids_slices.get('ic_antennas',   _empty('ic_antennas'))
            cs  = ids_slices.get('core_sources',  _empty('core_sources'))
            dis = ids_slices.get('distributions', _empty('distributions'))
            dsr = ids_slices.get('distribution_sources', _empty('distribution_sources'))
            nbi = ids_slices.get('nbi',           _empty('nbi'))
            wall = ids_slices.get('wall',         _empty('wall'))

            for ids_name, ids_obj in (
                ('equilibrium', eq),
                ('core_profiles', cp),
                ('ec_launchers', ec),
                ('ic_antennas', ic),
                ('core_sources', cs),
                ('distributions', dis),
                ('distribution_sources', dsr),
                ('nbi', nbi),
                ('wall', wall),
            ):
                _prepare_actor_input(ids_name, ids_obj, cp, timenow)

            output_ids = {}

            # ----------------------------------------------------------------
            # EC branch — torbeam
            # ----------------------------------------------------------------
            ec_power = _ec_total_power(ec)
            print(f"[driver] EC power = {ec_power/1e6:.3f} MW", flush=True)

            if 'torbeam' in active_actors:
                _send(instance, 'equilibrium_out',   eq,  timenow, t_next)
                _send(instance, 'core_profiles_out', cp,  timenow, t_next)
                _send(instance, 'ec_launchers_out',  ec,  timenow, t_next)
                waves_ec = _recv(instance, 'waves_in', 'waves', timenow)
            else:
                waves_ec = _empty('waves')

            output_ids['waves'] = waves_ec

            # ----------------------------------------------------------------
            # NBI FP branch — Rabbit (stateful; advance on every time slice)
            # ----------------------------------------------------------------
            distributions = dis
            distribution_sources = dsr
            if rabbit_enabled:
                distributions, distribution_sources = _run_rabbit(
                    instance, cp, eq, nbi, wall, timenow, t_next, dt)
                output_ids['distributions'] = distributions
                output_ids['distribution_sources'] = distribution_sources

            # ----------------------------------------------------------------
            # IC branch — cyrano  (only if wired)
            # ----------------------------------------------------------------
            ic_power = _ic_total_power(ic)
            ic_active = abs(ic_power) > POWER_EPS_W
            print(f"[driver] IC power = {ic_power/1e6:.3f} MW", flush=True)

            if 'cyrano' in active_actors and ic_active:
                _send(instance, 'equilibrium_out_ic',          eq,      timenow, t_next)
                _send(instance, 'core_profiles_out_ic',        cp,      timenow, t_next)
                _send(instance, 'ic_antennas_out',             ic,      timenow, t_next)
                _send(instance, 'waves_out_to_cyrano',         waves_ec, timenow, t_next)
                _send(instance, 'distributions_out_ic',
                      distributions, timenow, t_next)
                _send(instance, 'distribution_sources_out_ic',
                      distribution_sources, timenow, t_next)
                _send(instance, 'core_sources_out_ic',         cs,      timenow, t_next)
                _send(instance, 'nbi_out_ic',                  nbi,     timenow, t_next)
                waves_ic = _recv(instance, 'waves_ic_in', 'waves', timenow)
            else:
                if 'cyrano' in active_actors:
                    print("[driver] Skipping Cyrano because IC launched power is zero", flush=True)
                waves_ic = _empty('waves')

            # ----------------------------------------------------------------
            # Merge waves  (only if wired)
            # ----------------------------------------------------------------
            if 'merge_waves' in active_actors and ec_power > POWER_EPS_W and ic_active:
                _send(instance, 'waves_ec_out', waves_ec, timenow, t_next)
                _send(instance, 'waves_ic_out', waves_ic, timenow, t_next)
                waves = _recv(instance, 'waves_merged_in', 'waves', timenow)
            elif ic_active and ec_power <= POWER_EPS_W:
                if 'merge_waves' in active_actors:
                    print("[driver] Skipping merge_waves because EC launched power is zero", flush=True)
                waves = waves_ic
            else:
                if 'merge_waves' in active_actors and not ic_active:
                    print("[driver] Skipping merge_waves because IC launched power is zero", flush=True)
                waves = waves_ec

            output_ids['waves'] = waves

            # ----------------------------------------------------------------
            # FP branch — fopla  (only if wired)
            # ----------------------------------------------------------------
            if 'fopla' in active_actors and ic_active:
                _send(instance, 'equilibrium_out_fp',           eq,  timenow, t_next)
                _send(instance, 'core_profiles_out_fp',         cp,  timenow, t_next)
                _send(instance, 'ic_antennas_out_fp',           ic,  timenow, t_next)
                # FoPla is the IC Fokker-Planck actor; feeding merged EC+IC
                # waves can make it pick the EC wave first and crash in its
                # RF interpolation. Keep merged waves for downstream storage
                # and hcd2core_sources, but feed FoPla the IC wave branch.
                _send(instance, 'waves_out_to_fopla',           waves_ic, timenow, t_next)
                _send(instance, 'distributions_out_fp',
                      distributions, timenow, t_next)
                _send(instance, 'distribution_sources_out_fp',
                      distribution_sources, timenow, t_next)
                _send(instance, 'nbi_out_fp',                   nbi, timenow, t_next)
                distributions = _recv(instance, 'distributions_in', 'distributions', timenow)
                output_ids['distributions'] = distributions
            else:
                if 'fopla' in active_actors:
                    print("[driver] Skipping FoPla because IC launched power is zero", flush=True)

            # ----------------------------------------------------------------
            # Post-processing — hcd2core_sources  (only if wired)
            # ----------------------------------------------------------------
            if 'hcd2core_sources' in active_actors:
                _send(instance, 'distributions_out_post',         distributions, timenow, t_next)
                _send(instance, 'distribution_sources_out_post',
                      distribution_sources, timenow, t_next)
                _send(instance, 'waves_out_post',                 waves,         timenow, t_next)
                _send(instance, 'core_profiles_out_post',         cp,            timenow, t_next)
                core_sources = _recv(instance, 'core_sources_in', 'core_sources', timenow)
                output_ids['core_sources'] = core_sources

            # ----------------------------------------------------------------
            # Write results to DB
            # ----------------------------------------------------------------
            store_ids_slices(
                outputDb, inputMds, ids_slices, output_ids, m3_flag=1,
                param_process=param_process, timenow=timenow,
                config_folder_path=config_path,
            )

            timenow += dt

    print(f"[driver] Finished after {step} steps", flush=True)

    inputDb.close()
    outputDb.close()
    machineDb.close()
    print(f"[driver] Databases closed", flush=True)


if __name__ == "__main__":
    main()
