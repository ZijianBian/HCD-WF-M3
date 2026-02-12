"""
Workflow Driver with MUSCLE3 Support
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
"""

import copy
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
    Workflow Driver with MUSCLE3 support.
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
            print("[WorkflowDriver] Initialized in Hybrid M3 mode", file=sys.stdout, flush=True)
        else:
            print("[WorkflowDriver] Initialized in traditional iwrap mode", file=sys.stdout, flush=True)

    # =========================================================================
    # M3 Port Mapping & Instance Initialization
    # =========================================================================

    def _init_m3_port_mapping(self):
        self.m3_port_mapping = {}
        process_bundle = self.workflowObject.workflowData.process_bundle
        catdict = self.workflowObject.workflowData.catdict
        param_process = self.workflowObject.workflowData.getParamProcess()

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
                'ids_to_port': {ids: f"{ids}_out" for ids in input_ids},
                'port_to_ids': {f"{ids}_in": ids for ids in output_ids},
            }

        print(f"[WorkflowDriver] M3 port mapping:", file=sys.stdout, flush=True)
        for proc, cfg in self.m3_port_mapping.items():
            print(f"  {proc} ({cfg['code_name']}): in={cfg['input_ids']}, out={cfg['output_ids']}", flush=True)

    def _get_all_m3_ports(self):
        all_output_ports, all_input_ports = set(), set()
        for config in self.m3_port_mapping.values():
            for ids in config['input_ids']: all_output_ports.add(f"{ids}_out")
            for ids in config['output_ids']: all_input_ports.add(f"{ids}_in")
        return {'output_ports': sorted(list(all_output_ports)), 'input_ports': sorted(list(all_input_ports))}

    def _init_m3_instance(self):
        all_ports = self._get_all_m3_ports()
        ports = {Operator.O_I: all_ports['output_ports'], Operator.S: all_ports['input_ports']}
        print(f"[WorkflowDriver] Creating M3 Instance\n  O_I: {ports[Operator.O_I]}\n  S:   {ports[Operator.S]}", flush=True)
        return Instance(ports, InstanceFlags.SKIP_MMSF_SEQUENCE_CHECKS)

    # =========================================================================
    # Proxy Actor Injection (The Magic)
    # =========================================================================

    def _inject_m3_proxies(self):
        """
        Dynamically replace external actors in the executor with MUSCLE3 Proxies.
        """
        for process_name, port_config in self.m3_port_mapping.items():
            actor_name = port_config['code_name']

            def create_proxy(proc_name, config):
                def m3_proxy_actor(*inputargs):
                    print(f"  [M3 Proxy] Intercepted execution for {proc_name} ({config['code_name']})", flush=True)
                    
                    m3_timestamp = self.current_time

                    # 1. Send all input parameters
                    for idx, ids_name in enumerate(config['input_ids']):
                        port_name = config['ids_to_port'][ids_name]
                        # ======================================================
                        # If this port was already sent by another Actor at this time step,
                        # MUSCLE3 has broadcast it, so skip to avoid queue buildup and timing errors.
                        # ======================================================
                        if port_name in self._sent_ports_this_step:
                            print(f"    -> Skipping {port_name} (already broadcasted to M3 this step)", flush=True)
                            continue

                        ids_data = inputargs[idx]
                        internal_t = float(ids_data.time[-1]) if hasattr(ids_data, 'time') and len(ids_data.time) > 0 else 0.0
                        
                        if hasattr(ids_data, 'time'):
                            import numpy as np
                            ids_data.time = np.array([m3_timestamp], dtype=np.float64)
                            if hasattr(ids_data, 'ids_properties'):
                                ids_data.ids_properties.homogeneous_time = 1

                        print(f"    -> Sending {port_name} (M3_t={m3_timestamp:.2f}, internal_t updated: {internal_t:.4f} -> {m3_timestamp:.2f})", flush=True)
                        
                        self.m3_instance.send(port_name, Message(m3_timestamp, data=ids_data.serialize()))
                        
                        # Mark this port as already sent
                        self._sent_ports_this_step.add(port_name)

                    # 2. Wait for and receive the computed outputs
                    received_outputs = []
                    for port_name, ids_name in config['port_to_ids'].items():
                        print(f"    <- Waiting for {port_name}...", flush=True)
                        msg = self.m3_instance.receive(port_name)
                        
                        output_ids = _create_ids(ids_name)
                        output_ids.deserialize(msg.data)
                        
                        if not getattr(output_ids, '__name__', None):
                            object.__setattr__(output_ids, '__name__', ids_name)

                        print(f"    <- Received {ids_name} (M3_t={msg.timestamp:.2f})", flush=True)
                        received_outputs.append(output_ids)

                    # 3. Return matching original actor format
                    return received_outputs[0] if len(received_outputs) == 1 else received_outputs
                return m3_proxy_actor

            self.workflowObject.workflowData.dictionary_of_actors[actor_name] = create_proxy(process_name, port_config)
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
        print(f"---- Enter time loop (Mode: {'Hybrid M3' if self.m3_flag == 1 else 'iwrap'}) ----", flush=True)

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
        self._sent_ports_this_step = set()

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
                pass # Non-critical if missing
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