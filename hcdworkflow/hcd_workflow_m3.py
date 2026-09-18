#!/usr/bin/env python
"""Expose HCDWorkflow and its iWrap actors as one MUSCLE3 micro model.

Each reuse processes one IDS slice at the macro/PDS controller's timestamp
and returns its outputs with the same timestamp and next_timestamp.

MUSCLE3 Manager launches this script as:
    python hcd_workflow_m3.py <config_folder_path>
"""

import logging
import math
import sys

from libmuscle import Instance, Message, InstanceFlags
from ymmsl import Operator

from hcdworkflow.hcd_workflow import HCDWorkflow
from workflow.ids_prep import _create_ids, _smart_convert


# =============================================================================
# Port Definitions (must match workflow_driver and ymmsl)
# =============================================================================

# Ports that receive IDS from macro (F_INIT)
RECV_PORTS = [
    "equilibrium_in",
    "core_profiles_in",
    "workflow_in",
    "ec_launchers_in",
    "ic_antennas_in",
    "core_sources_in",
    "distributions_in",
    "distribution_sources_in",
    "nbi_in",
    "wall_in",
]

# Ports that send IDS back to macro (O_F)
SEND_PORTS = [
    "core_sources_out",
    "waves_out",
    "core_profiles_out",
    "distributions_out",
    "distribution_sources_out",
]


# PDS invokes this micro once for each externally scheduled time slice.  The
# tolerance is only for floating-point transport noise, not for accepting a
# different physical time.
PDS_TIME_TOLERANCE = 1.0e-9


def _port_to_ids(port_name):
    """Convert port name to IDS name: 'equilibrium_in' → 'equilibrium'."""
    return port_name.rsplit("_", 1)[0]


def _validate_pds_clock(messages, time_envelope):
    """Return the PDS timestamp after checking that one HCD slice is synchronous."""
    if not messages:
        raise ValueError("PDS invocation has no connected input messages")

    tbegin, tend = time_envelope
    _, reference_message = next(iter(messages.items()))
    timestamp = reference_message.timestamp
    if not math.isfinite(timestamp):
        raise ValueError("PDS input timestamp must be finite")
    if not all(math.isfinite(bound) for bound in (tbegin, tend)):
        raise ValueError("HCD XML time bounds must be finite")

    for port_name, message in messages.items():
        if not math.isclose(message.timestamp, timestamp, rel_tol=0.0, abs_tol=PDS_TIME_TOLERANCE):
            raise ValueError(
                "PDS input timestamps disagree: " f"{port_name}={message.timestamp:.17g}, expected {timestamp:.17g}"
            )

    # Negative XML bounds request the standalone driver's database-derived
    # limits. This micro has no database access, so only explicit nonnegative
    # bounds constrain its incoming controller time. Synchrony is still checked.
    before_start = tbegin >= 0 and timestamp < tbegin - PDS_TIME_TOLERANCE
    after_end = tend >= 0 and timestamp > tend + PDS_TIME_TOLERANCE
    if before_start or after_end:
        raise ValueError(
            "PDS timestamp " f"{timestamp:.17g} is outside the HCD XML time envelope " f"[{tbegin:.17g}, {tend:.17g}]"
        )

    # next_timestamp belongs to the PDS controller.  Preserve it without
    # imposing an HCD-specific future-time policy.
    return timestamp, reference_message.next_timestamp


def _shutdown_for_timing_error(instance, error):
    """Report a clock-contract violation to MUSCLE3 before stopping this micro."""
    message = f"[hcd_workflow] PDS clock contract violation: {error}"
    print(message, flush=True, file=sys.stderr)
    instance.error_shutdown(message)
    raise RuntimeError(message) from error


def _deserialize_ids(instance, port_name, message):
    """Allow absent IDS payloads, but stop on a corrupt transmitted IDS."""
    ids_obj = _create_ids(_port_to_ids(port_name))
    if message.data is not None and len(message.data) > 0:
        try:
            ids_obj.deserialize(message.data)
        except Exception as error:
            text = f"[hcd_workflow] Could not deserialize IDS from {port_name}"
            instance.error_shutdown(text)
            raise RuntimeError(text) from error
    return ids_obj


def _serialize_ids(instance, port_name, ids_obj):
    """Encode an absent output explicitly; never hide a serialization error."""
    if ids_obj is None or ids_obj.ids_properties.homogeneous_time < 0:
        return b""
    try:
        return ids_obj.serialize()
    except Exception as error:
        text = f"[hcd_workflow] Could not serialize IDS for {port_name}"
        instance.error_shutdown(text)
        raise RuntimeError(text) from error


def _run_workflow_for_slice(workflow, ids_slices, timestamp):
    """Inject one received M3 slice into ``HCDWorkflow`` and execute it."""
    workflow.setProcessStatus(timestamp)

    mandatory_keys = ("equilibrium", "core_profiles", "workflow")
    mandatory = {key: ids_slices[key] for key in mandatory_keys if key in ids_slices}
    optional = {key: value for key, value in ids_slices.items() if key not in mandatory_keys}

    for key in mandatory_keys:
        if key not in mandatory:
            mandatory[key] = _create_ids(key)

    result = workflow.run(
        equilibrium=mandatory["equilibrium"],
        core_profiles=mandatory["core_profiles"],
        workflow=mandatory["workflow"],
        **optional,
    )
    if result is None:
        raise RuntimeError(f"HCD workflow failed at t={timestamp:.17g}")
    return result


# =============================================================================
# Main: Micro Model
# =============================================================================


def main():
    logging.basicConfig(level=logging.INFO)
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    if len(sys.argv) < 2:
        print("Usage: python hcd_workflow_m3.py <config_folder_path>")
        sys.exit(1)

    config_path = sys.argv[1]
    print("[hcd_workflow] Starting micro model", flush=True)
    print(f"[hcd_workflow] Config: {config_path}", flush=True)

    # === 1. Create MUSCLE3 Instance ===
    ports = {
        Operator.F_INIT: RECV_PORTS,
        Operator.O_F: SEND_PORTS,
    }
    instance = Instance(ports, InstanceFlags.KEEPS_NO_STATE_FOR_NEXT_USE)

    print("[hcd_workflow] M3 Instance created", flush=True)
    print(f"  F_INIT (recv ← macro): {RECV_PORTS}", flush=True)
    print(f"  O_F    (send → macro): {SEND_PORTS}", flush=True)

    # === 2. Initialize the original HCDWorkflow ===
    # This sets up the actor registry, dependency graph, and iWrap bindings.
    # No database access needed here — all IDS come via M3 from the macro.
    workflow = HCDWorkflow()
    workflow.initialize(config_path)
    print("[hcd_workflow] HCDWorkflow initialized (iWrap actors loaded)", flush=True)

    pds_time_envelope = (workflow.workflowData.tbegin, workflow.workflowData.tend)
    print(
        "[hcd_workflow] PDS time envelope: "
        f"[{pds_time_envelope[0]:.17g}, {pds_time_envelope[1]:.17g}] s "
        "(one_time_slice is ignored by the PDS outer clock)",
        flush=True,
    )

    # === 3. Determine connected ports ===
    connected_recv = [p for p in RECV_PORTS if instance.is_connected(p)]
    connected_send = [p for p in SEND_PORTS if instance.is_connected(p)]
    print(f"[hcd_workflow] Connected recv ports: {connected_recv}", flush=True)
    print(f"[hcd_workflow] Connected send ports: {connected_send}", flush=True)

    # === 4. Reuse loop: one iteration per timestep ===
    iteration = 0

    while instance.reuse_instance():
        iteration += 1
        print(f"[hcd_workflow] --- Iteration {iteration} ---", flush=True)

        # --- F_INIT: Receive all input IDS ---
        ids_slices = {}
        messages = {}

        for port_name in connected_recv:
            ids_name = _port_to_ids(port_name)
            msg = instance.receive(port_name)
            messages[port_name] = msg

            ids_obj = _deserialize_ids(instance, port_name, msg)
            ids_slices[ids_name] = ids_obj
            print(
                f"  <- Received {ids_name} " f"(t={msg.timestamp}, next_t={msg.next_timestamp})",
                flush=True,
            )

        try:
            timestamp, next_timestamp = _validate_pds_clock(messages, pds_time_envelope)
        except ValueError as error:
            _shutdown_for_timing_error(instance, error)

        # Apply the same input preparation as the standalone driver.
        for ids_name, ids_obj in ids_slices.items():
            ids_obj = _smart_convert(ids_obj, ids_name)
            object.__setattr__(ids_obj, "__name__", ids_name)
            ids_slices[ids_name] = ids_obj

        # --- Compute: call original HCDWorkflow.run() ---
        # iWrap actors execute internally — M3 knows nothing about them.
        print(f"[hcd_workflow] Running HCDWorkflow.run() at t={timestamp:.4f}...", flush=True)

        output_ids = _run_workflow_for_slice(workflow, ids_slices, timestamp)

        print("[hcd_workflow] HCDWorkflow.run() completed", flush=True)

        # --- O_F: Send output IDS back ---
        # Build set of IDS types that SHOULD have been produced
        expected_outputs = set()
        for process, bundle in workflow.workflowData.process_bundle.items():
            if bundle.get("status") == 1 and "merge_" not in process:
                for ids_name in bundle.get("output", {}).keys():
                    expected_outputs.add(ids_name)

        for port_name in connected_send:
            ids_name = _port_to_ids(port_name)
            ids_data = output_ids.get(ids_name)

            if ids_data is not None:
                # A homogeneous output slice belongs to the controller time,
                # even when its prescribed geometry was sampled by nearest time.
                if ids_data.ids_properties.homogeneous_time == 1 and len(ids_data.time) == 1:
                    ids_data.time[0] = timestamp
            else:
                if ids_name in expected_outputs:
                    print(f"  -> WARNING: {ids_name} expected but missing!", flush=True, file=sys.stderr)
            serialized = _serialize_ids(instance, port_name, ids_data)

            print(
                f"  -> Sending {ids_name} on {port_name} "
                f"(t={timestamp:.4f}, next_t={next_timestamp}, {len(serialized)} bytes)",
                flush=True,
            )
            instance.send(
                port_name,
                Message(timestamp, next_timestamp=next_timestamp, data=serialized),
            )

        print(f"[hcd_workflow] Iteration {iteration} complete", flush=True)

    print(f"[hcd_workflow] Finished after {iteration} iterations", flush=True)


if __name__ == "__main__":
    main()
