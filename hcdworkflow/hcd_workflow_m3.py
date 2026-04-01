#!/usr/bin/env python
"""
hcd_workflow_m3.py — MUSCLE3 Micro Model (HCD Workflow)

Architecture:
    wf_wrapper_m3.py (macro)
        ↕  M3 conduits (individual IDS ports)
    hcd_workflow_m3.py (this file, micro)
        └── HCDWorkflow.run() with iWrap actors (invisible to M3)

Responsibilities:
    - Initialize MUSCLE3 Instance with per-IDS ports
    - Initialize HCDWorkflow (for actor registry and execution logic)
    - Enter reuse loop (one iteration per timestep from macro)
    - Receive IDS from wf_wrapper via M3
    - Call the original HCDWorkflow.run() — iWrap actors execute internally
    - Send updated IDS back to wf_wrapper via M3

The iWrap actors (Torbeam, hcd2core_sources, etc.) are called inside
HCDWorkflow.run() and are completely invisible to MUSCLE3.

Usage (launched by MUSCLE3 Manager, not directly):
    python hcd_workflow_m3.py <config_folder_path>
"""

import logging
import os
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import imas

from libmuscle import Instance, Message, KEEPS_NO_STATE_FOR_NEXT_USE
from ymmsl import Operator

from hcdworkflow.hcd_workflow import HCDWorkflow

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


# =============================================================================
# Port Definitions (must match wf_wrapper and ymmsl)
# =============================================================================

# Ports that receive IDS from macro (F_INIT)
RECV_PORTS = [
    'equilibrium_in',
    'core_profiles_in',
    'workflow_in',
    'ec_launchers_in',
    'ic_antennas_in',
    'core_sources_in',
    'distributions_in',
    'distribution_sources_in',
]

# Ports that send IDS back to macro (O_F)
SEND_PORTS = [
    'core_sources_out',
    'waves_out',
    'core_profiles_out',
    'distributions_out',
]


def _port_to_ids(port_name):
    """Convert port name to IDS name: 'equilibrium_in' → 'equilibrium'."""
    return port_name.rsplit('_', 1)[0]


def _create_ids(ids_name: str):
    """Create an empty IDS object by name."""
    if hasattr(imas, 'IDSFactory'):
        factory = imas.IDSFactory()
        return getattr(factory, ids_name)()
    elif hasattr(imas, ids_name):
        return getattr(imas, ids_name)()
    else:
        raise AttributeError(f"Cannot create IDS '{ids_name}': not found in imas module")


# =============================================================================
# Main: Micro Model
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python hcd_workflow_m3.py <config_folder_path>")
        sys.exit(1)

    config_path = sys.argv[1]
    print(f"[hcd_workflow] Starting micro model", flush=True)
    print(f"[hcd_workflow] Config: {config_path}", flush=True)

    # === 1. Create MUSCLE3 Instance ===
    ports = {
        Operator.F_INIT: RECV_PORTS,
        Operator.O_F:    SEND_PORTS,
    }
    instance = Instance(ports, KEEPS_NO_STATE_FOR_NEXT_USE)

    print(f"[hcd_workflow] M3 Instance created", flush=True)
    print(f"  F_INIT (recv ← macro): {RECV_PORTS}", flush=True)
    print(f"  O_F    (send → macro): {SEND_PORTS}", flush=True)

    # === 2. Initialize the original HCDWorkflow ===
    # This sets up the actor registry, dependency graph, and iWrap bindings.
    # No database access needed here — all IDS come via M3 from the macro.
    workflow = HCDWorkflow()
    workflow.initialize(config_path)
    print(f"[hcd_workflow] HCDWorkflow initialized (iWrap actors loaded)", flush=True)

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
        timestamp = 0.0

        for port_name in connected_recv:
            ids_name = _port_to_ids(port_name)
            msg = instance.receive(port_name)
            timestamp = msg.timestamp

            ids_obj = _create_ids(ids_name)
            if msg.data and len(msg.data) > 0:
                try:
                    ids_obj.deserialize(msg.data)
                except Exception as e:
                    print(f"  <- WARNING: Could not deserialize {ids_name}: {e}", flush=True)
            # workflow_executor expects __name__ on every IDS object
            object.__setattr__(ids_obj, '__name__', ids_name)
            ids_slices[ids_name] = ids_obj
            print(f"  <- Received {ids_name} (t={timestamp:.4f})", flush=True)

        # --- Compute: call original HCDWorkflow.run() ---
        # iWrap actors execute internally — M3 knows nothing about them.
        print(f"[hcd_workflow] Running HCDWorkflow.run() at t={timestamp:.4f}...", flush=True)

        workflow.setProcessStatus(timestamp)

        # Separate mandatory and optional IDS
        mandatory_keys = ("equilibrium", "core_profiles", "workflow")
        mandatory = {k: ids_slices[k] for k in mandatory_keys if k in ids_slices}
        optional = {k: v for k, v in ids_slices.items() if k not in mandatory_keys}

        # Provide empty mandatory IDS if not received (safety)
        for k in mandatory_keys:
            if k not in mandatory:
                mandatory[k] = _create_ids(k)

        workflow.run(
            equilibrium=mandatory["equilibrium"],
            core_profiles=mandatory["core_profiles"],
            workflow=mandatory["workflow"],
            **optional,
        )

        print(f"[hcd_workflow] HCDWorkflow.run() completed", flush=True)

        # --- O_F: Send output IDS back ---
        output_ids = workflow._getIDSes()
##################
        for k, v in output_ids.items():
            print(f"  _getIDSes: {k} -> {type(v)}", flush=True)
######################
        # Build set of IDS types that SHOULD have been produced
        expected_outputs = set()
        for process, bundle in workflow.workflowData.process_bundle.items():
            if bundle.get("status") == 1 and "merge_" not in process:
                for ids_name in bundle.get("output", {}).keys():
                    expected_outputs.add(ids_name)

        for port_name in connected_send:
            ids_name = _port_to_ids(port_name)
            ids_data = output_ids.get(ids_name)

            serialized = None
            if ids_data is not None:
                try:
                    serialized = ids_data.serialize()
                except (ValueError, RuntimeError) as e:
                    print(f"  -> ERROR: {ids_name} serialization failed: {e}", flush=True)

            if serialized is None:
                if ids_name in expected_outputs:
                    print(
                        f"  -> WARNING: {ids_name} expected but missing!",
                        flush=True, file=sys.stderr
                    )
                empty_ids = _create_ids(ids_name)
                empty_ids.ids_properties.homogeneous_time = -1
                try:
                    serialized = empty_ids.serialize()
                except Exception:
                    serialized = b''

            print(f"  -> Sending {ids_name} on {port_name} (t={timestamp:.4f}, {len(serialized)} bytes)", flush=True)
            instance.send(port_name, Message(timestamp, data=serialized))

        print(f"[hcd_workflow] Iteration {iteration} complete", flush=True)

    print(f"[hcd_workflow] Finished after {iteration} iterations", flush=True)


if __name__ == "__main__":
    main()