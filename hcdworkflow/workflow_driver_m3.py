"""
Workflow Driver with MUSCLE3 Support (Vector Port / Bundle Mode)
Architecture:
    wf_wrapper_m3.py (entry point)
      └── WorkflowDriver (this file)
            ├── m3_flag=0: Calls original HCDWorkflow.run() directly
            └── m3_flag=1: Injects M3 Proxy Actors → Calls original run()
                  └── HCDWorkflow (original, unchanged)
                        └── WorkflowExecutor (original, unchanged)
                            └── M3 Proxy Actor (intercepts execution, sends/recvs via M3)

In M3 mode, the workflow executor naturally resolves dependencies and calls actors.
Instead of running physics, the injected Proxy Actor sends the inputs via MUSCLE3,
waits for the remote actor to finish, and returns the real results back to the executor.

Communication via MUSCLE3 vector ports:
    hcd_workflow (macro)                actor_wrapper[i] (micro)
    ───────────────────                 ────────────────────────
    O_I: actor_input[i]  ──conduit──>  F_INIT: actor_input
    S:   actor_output[i] <──conduit──  O_F:    actor_output

    Each message is a bundled dict: {ids_name: serialized_bytes, ...}
    packed via msgpack for efficient binary transfer.

NOTE on vector ports:
    - In the ymmsl file, port names are plain identifiers (e.g., "actor_input")
    - In the Python Instance() constructor, we append "[]" to declare vector ports
    - MUSCLE3 auto-detects vector nature from the multiplicity of actor_wrapper
"""

import copy
import json
import logging
import os
import sys

# Force unbuffered stdout/stderr for reliable logging under MUSCLE3
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import imas

from hcdworkflow.hcd_workflow import HCDWorkflow

log = logging.getLogger()
log.setLevel(logging.ERROR)

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Optional MUSCLE3 imports
M3_AVAILABLE = False
try:
    from libmuscle import Instance, Message, KEEPS_NO_STATE_FOR_NEXT_USE, InstanceFlags
    from ymmsl import Operator
    M3_AVAILABLE = True
except ImportError:
    print("[WorkflowDriver] Warning: MUSCLE3 not available", file=sys.stderr)

# msgpack for efficient binary bundling of multiple IDS
MSGPACK_AVAILABLE = False
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    print("[WorkflowDriver] Warning: msgpack not available, falling back to json", file=sys.stderr)


# =============================================================================
# Bundle Serialization Helpers
# =============================================================================

def _pack_bundle(bundle_dict):
    """Pack a dict of {ids_name: bytes} into a single bytes payload."""
    if MSGPACK_AVAILABLE:
        return msgpack.packb(bundle_dict, use_bin_type=True)
    else:
        # Fallback: json with base64 encoding for bytes values
        import base64
        json_dict = {k: base64.b64encode(v).decode('ascii') for k, v in bundle_dict.items()}
        return json.dumps(json_dict).encode('utf-8')


def _unpack_bundle(data):
    """Unpack a bytes payload back into a dict of {ids_name: bytes}."""
    if MSGPACK_AVAILABLE:
        return msgpack.unpackb(data, raw=True)
    else:
        import base64
        json_dict = json.loads(data.decode('utf-8'))
        return {k: base64.b64decode(v) for k, v in json_dict.items()}


# =============================================================================
# Utility Functions
# =============================================================================

def _safe_partial_get(db_entry, ids_name: str, data_path: str, occurrence: int = 0):
    """Safely get a partial IDS field from a database entry."""
    try:
        if hasattr(db_entry, 'partial_get'):
            return db_entry.partial_get(ids_name=ids_name, data_path=data_path, occurrence=occurrence)
        else:
            try:
                ids_object = db_entry.get(ids_name, occurrence)
                result = ids_object
                for part in data_path.split('/'):
                    if part:
                        result = getattr(result, part)
                return result
            except Exception as e:
                if 'empty' in str(e).lower():
                    print(f"  IDS '{ids_name}' is empty")
                    return None
                raise
    except Exception as e:
        print(f"  ERROR in _safe_partial_get({ids_name}, {data_path}): {e}")
        return None


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
# WorkflowDriver
# =============================================================================

class WorkflowDriver:
    """
    Workflow Driver with MUSCLE3 support using vector port bundle messaging.
    """

    def __init__(self, workflowConfigPath: str, m3_flag=0):
        self.m3_flag = m3_flag
        self.m3_instance = None
        self.workflowConfigPath = workflowConfigPath

        # Use the ORIGINAL HCDWorkflow (no M3 modifications needed)
        self.workflowObject = HCDWorkflow()
        self.workflowObject.initialize(workflowConfigPath)

        if m3_flag == 1:
            if not M3_AVAILABLE:
                raise RuntimeError("MUSCLE3 mode requested but libmuscle is not available!")
            self._init_m3_port_mapping()
            self.m3_instance = self._init_m3_instance()
            print("[WorkflowDriver] Initialized in Hybrid M3 mode (vector port bundle)", file=sys.stdout, flush=True)
        else:
            print("[WorkflowDriver] Initialized in traditional iwrap mode", file=sys.stdout, flush=True)

    # =========================================================================
    # M3 Port Mapping & Instance Initialization
    # =========================================================================

    def _init_m3_port_mapping(self):
        """
        Build mapping: process_name -> {code_name, input_ids, output_ids, slot_index}

        slot_index determines which actor_wrapper instance (vector port slot)
        this process communicates with. The order matches the ymmsl settings:
            actor_wrapper[0] = first external process
            actor_wrapper[1] = second external process
            ...
        """
        self.m3_port_mapping = {}
        process_bundle = self.workflowObject.workflowData.process_bundle
        catdict = self.workflowObject.workflowData.catdict
        param_process = self.workflowObject.workflowData.getParamProcess()

        slot_index = 0
        for process_name in process_bundle.keys():
            if "merge_" in process_name or process_name not in catdict:
                continue

            choice = param_process.get(process_name, 0)
            if choice == 0:
                continue

            codeinfo = catdict[process_name][choice]
            code_name = codeinfo["name"]
            input_ids = list(codeinfo.get("input", []))
            output_ids = list(codeinfo.get("output", []))

            self.m3_port_mapping[process_name] = {
                'code_name': code_name,
                'input_ids': input_ids,
                'output_ids': output_ids,
                'slot_index': slot_index,
            }
            slot_index += 1

        print(f"[WorkflowDriver] M3 port mapping (vector port bundle mode):", file=sys.stdout, flush=True)
        for proc, cfg in self.m3_port_mapping.items():
            print(f"  slot[{cfg['slot_index']}] {proc} ({cfg['code_name']}): "
                  f"in={cfg['input_ids']}, out={cfg['output_ids']}", flush=True)

        self.num_actor_slots = slot_index
        print(f"[WorkflowDriver] Total actor slots: {self.num_actor_slots}", flush=True)

    def _init_m3_instance(self):
        """
        Create MUSCLE3 Instance with vector ports.

        NOTE: The '[]' suffix is the Python-side declaration that tells MUSCLE3
        this port is a vector port. The ymmsl file uses plain names without [].
        MUSCLE3 auto-sizes the vector port based on the multiplicity of
        the connected component (actor_wrapper).
        """
        ports = {
            Operator.O_I: ['actor_input[]'],
            Operator.S:   ['actor_output[]'],
        }
        print(f"[WorkflowDriver] Creating M3 Instance with vector ports", flush=True)
        print(f"  O_I: actor_input[] ({self.num_actor_slots} slots)", flush=True)
        print(f"  S:   actor_output[] ({self.num_actor_slots} slots)", flush=True)
        return Instance(ports, InstanceFlags.SKIP_MMSF_SEQUENCE_CHECKS)

    # =========================================================================
    # Proxy Actor Injection (The Magic)
    # =========================================================================

    def _inject_m3_proxies(self):
        """
        Dynamically replace external actors in the executor with MUSCLE3 Proxies.

        Each proxy:
        1. Bundles all input IDS into a single message (dict of serialized bytes)
        2. Sends it to actor_input[slot_index] via the vector port
        3. Receives the bundled result from actor_output[slot_index]
        4. Unpacks and returns the output IDS
        """
        for process_name, port_config in self.m3_port_mapping.items():
            actor_name = port_config['code_name']

            def create_proxy(proc_name, config):
                def m3_proxy_actor(*inputargs):
                    slot_idx = config['slot_index']
                    print(f"  [M3 Proxy] Intercepted {proc_name} ({config['code_name']}) -> slot[{slot_idx}]", flush=True)

                    m3_timestamp = self.current_time

                    # === 1. Bundle all input IDS into one message ===
                    bundle = {}
                    for idx, ids_name in enumerate(config['input_ids']):
                        ids_data = inputargs[idx]

                        # Align IDS timestamp with M3 timestamp
                        if hasattr(ids_data, 'time') and len(ids_data.time) > 0:
                            import numpy as np
                            ids_data.time = np.array([m3_timestamp], dtype=np.float64)
                            if hasattr(ids_data, 'ids_properties'):
                                ids_data.ids_properties.homogeneous_time = 1

                        bundle[ids_name] = ids_data.serialize()
                        print(f"    -> Bundled {ids_name} for slot[{slot_idx}]", flush=True)

                    # === 2. Send bundle to actor_input[slot_index] ===
                    packed = _pack_bundle(bundle)
                    print(f"    -> Sending bundle to actor_input[{slot_idx}] "
                          f"(t={m3_timestamp:.2f}, {len(config['input_ids'])} IDS, "
                          f"{len(packed)} bytes)", flush=True)
                    self.m3_instance.send('actor_input', Message(m3_timestamp, data=packed), slot_idx)

                    # === 3. Receive result bundle from actor_output[slot_index] ===
                    print(f"    <- Waiting for actor_output[{slot_idx}]...", flush=True)
                    msg = self.m3_instance.receive('actor_output', slot_idx)
                    result_bundle = _unpack_bundle(msg.data)
                    print(f"    <- Received bundle from slot[{slot_idx}] "
                          f"(t={msg.timestamp:.2f}, {len(result_bundle)} IDS)", flush=True)

                    # === 4. Unpack output IDS ===
                    received_outputs = []
                    for ids_name in config['output_ids']:
                        # Handle both str and bytes keys (msgpack may return bytes keys)
                        ids_name_key = ids_name
                        if len(result_bundle) > 0 and isinstance(list(result_bundle.keys())[0], bytes):
                            ids_name_key = ids_name.encode('utf-8')

                        output_ids = _create_ids(ids_name)
                        output_ids.deserialize(result_bundle[ids_name_key])

                        if not getattr(output_ids, '__name__', None):
                            object.__setattr__(output_ids, '__name__', ids_name)

                        print(f"    <- Unpacked {ids_name}", flush=True)
                        received_outputs.append(output_ids)

                    return received_outputs[0] if len(received_outputs) == 1 else received_outputs

                return m3_proxy_actor

            self.workflowObject.workflowData.dictionary_of_actors[actor_name] = create_proxy(process_name, port_config)
            print(f"[WorkflowDriver] Injected proxy for {actor_name} (slot[{port_config['slot_index']}])", flush=True)

    # =========================================================================
    # Initialization & Time Loop Core
    # =========================================================================

    def initialize(self, inputdb, outputdb, machineDb, inputIds, inputMds):
        self.inputDb, self.outputDb, self.md = inputdb, outputdb, machineDb
        self.inputIds, self.inputMds = inputIds, inputMds

    def executeTimeloop(self, one_time_slice=None, tbegin=None, tend=None, dt_required=None):
        if one_time_slice is not None: self.workflowObject.workflowData.one_time_slice = one_time_slice
        if tbegin is not None: self.workflowObject.workflowData.tbegin = tbegin
        if tend is not None: self.workflowObject.workflowData.tend = tend
        if dt_required is not None: self.workflowObject.workflowData.dt_required = dt_required

        self._prepareTimeRange()

        timenow = self.workflowObject.workflowData.tbegin
        tend_val = self.workflowObject.workflowData.tend
        dt = self.workflowObject.workflowData.dt_required
        nsteps = 1 if self.workflowObject.workflowData.one_time_slice else int((tend_val - timenow) / dt)
        if dt * nsteps < (tend_val - timenow): nsteps += 1

        print("---------------------------------------------", flush=True)
        print(f"---- Enter time loop (Mode: {'Hybrid M3 Vector Port' if self.m3_flag == 1 else 'iwrap'}) ----", flush=True)

        if self.m3_flag == 1:
            self._run_timeloop_m3(timenow, tend_val, dt, nsteps)
        else:
            self._run_timeloop_iwrap(timenow, tend_val, dt, nsteps)

        print("[WorkflowDriver] Time loop finished", flush=True)

    def _prepareTimeRange(self):
        if self.workflowObject.workflowData.one_time_slice == 0:
            time_array = _safe_partial_get(self.inputDb, ids_name="equilibrium", data_path="time")
            if time_array is None: return
            if self.workflowObject.workflowData.tbegin < 0: self.workflowObject.workflowData.tbegin = time_array[0]
            if self.workflowObject.workflowData.tend < 0: self.workflowObject.workflowData.tend = time_array[-1]
        else:
            self.workflowObject.workflowData.tend = self.workflowObject.workflowData.tbegin + self.workflowObject.workflowData.dt_required

    # =========================================================================
    # Traditional & MUSCLE3 Time Loops
    # =========================================================================

    def _run_timeloop_iwrap(self, timenow, tend, dt, nsteps):
        step = 0
        while timenow < tend:
            step += 1
            print(f"---------------------------------------------\nStep = {step}/{nsteps}, Time = {timenow:5.2f} s, dt = {dt:5.2f} s", flush=True)
            self._run_single_step(timenow)
            timenow += dt

    def _run_timeloop_m3(self, timenow, tend, dt, nsteps):
        self._inject_m3_proxies()

        while self.m3_instance.reuse_instance():
            step = 0
            try:
                while timenow < tend:
                    step += 1
                    print(f"---------------------------------------------\nStep = {step}/{nsteps}, Time = {timenow:5.2f} s, dt = {dt:5.2f} s", flush=True)
                    self._run_single_step(timenow)
                    timenow += dt
            except Exception as e:
                print(f"[WorkflowDriver] EXCEPTION at step {step}, t={timenow}: {e}", file=sys.stderr, flush=True)
                import traceback; traceback.print_exc(file=sys.stderr)
                raise
            # break  # Macro-model: only one reuse_instance() iteration

    def _run_single_step(self, timenow):
        """Unified step execution: works identically for M3 and IWRAP."""

        self.current_time = timenow

        idsSlices = self._getIDSSlices(timenow)
        if idsSlices is None: return

        nonmandatoryIDSes = {k: v for k, v in idsSlices.items() if k not in ["equilibrium", "core_profiles", "workflow"]}

        self.workflowObject.setProcessStatus(timenow)

        # In M3 Mode, calling run() triggers our Proxies automatically!
        self.workflowObject.run(
            equilibrium=idsSlices["equilibrium"],
            core_profiles=idsSlices["core_profiles"],
            workflow=idsSlices["workflow"],
            **nonmandatoryIDSes,
        )

        idsOut = self.workflowObject._getIDSes()
        self._storeIDSSlices(idsSlices, idsOut)

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _getIDSSlices(self, timenow):
        idsSlices = {}
        for ids in self.inputIds:
            try:
                idsSlices[ids] = self.inputDb.get_slice(ids, timenow, 1)
            except Exception as e:
                if 'empty' in str(e).lower(): idsSlices[ids] = _create_ids(ids)
                else: return None
        for ids in self.inputMds:
            try:
                idsSlices[ids] = self.md.get_slice(ids, timenow, 1)
            except Exception as e:
                pass  # Non-critical if missing
        return idsSlices

    def _storeIDSSlices(self, inputSlices, idsOut):
        for idsName, idsData in inputSlices.items():
            if idsName in self.inputMds: continue
            if hasattr(idsData, 'ids_properties') and idsData.ids_properties.homogeneous_time >= 0:
                self.outputDb.put_slice(idsData)

        for ids_name, ids_data in idsOut.items():
            if hasattr(ids_data, 'time') and len(ids_data.time) > 0:
                if ids_name != "equilibrium" and ids_data.time[0] > 0:
                    if self.m3_flag == 1:
                        # Re-serialize to avoid C-level segfaults in output db
                        clean_ids = _create_ids(ids_name)
                        clean_ids.deserialize(ids_data.serialize())
                        self.outputDb.put_slice(clean_ids)
                    else:
                        self.outputDb.put_slice(ids_data)