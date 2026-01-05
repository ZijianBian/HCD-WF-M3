"""
MUSCLE3 Workflow Driver for HCD-Workflow (Fortran Torbeam Compatible)

This driver directly communicates with the Fortran torbeam_m3.exe,
following the same architecture as the standalone Torbeam M3 workflow.

Key features:
- Direct communication with Fortran executable via MUSCLE3
- Same port structure as standalone Torbeam (coupling.ymmsl)

- Bypasses WorkflowDbHelper to be DD 4.0.0 compatible
"""

import logging
import os
import sys
import inspect
import copy
import numpy as np
from pathlib import Path

from libmuscle import Instance, Message, KEEPS_NO_STATE_FOR_NEXT_USE
from ymmsl import Operator

import imas

# Handle different IMAS versions (DD 3.x vs DD 4.0.0)
try:
    # DD 4.0.0 (new imas-python)
    from imas.ids_defs import MEMORY_BACKEND, HDF5_BACKEND, MDSPLUS_BACKEND
    USE_HAS_VALUE = True
    print("[Driver] Using IMAS DD 4.0.0 API (imas.ids_defs)")
except ImportError:
    # DD 3.x (old imas)
    from imas.imasdef import MEMORY_BACKEND, HDF5_BACKEND, MDSPLUS_BACKEND
    USE_HAS_VALUE = False
    print("[Driver] Using IMAS DD 3.x API (imas.imasdef)")

log = logging.getLogger()
log.setLevel(logging.ERROR)

# Check for waveform_cooker
isWaveformCookerPresent = True
try:
    from waveform_cooker import add_dynamic, ec_add_dynamic, ec_adjust
except Exception as e:
    isWaveformCookerPresent = False
    print(f"[Driver] Warning: waveform_cooker not available: {e}", file=sys.stderr)


def get_backend_id(backend_name):
    """Convert backend name string to IMAS backend constant."""
    backend_map = {
        'HDF5': HDF5_BACKEND,
        'MDSPLUS': MDSPLUS_BACKEND,
        'MEMORY': MEMORY_BACKEND,
    }
    return backend_map.get(backend_name.upper(), HDF5_BACKEND)


def parse_workflow_xml(xml_path):
    """Parse input_workflow.xml and extract parameters."""
    import xml.etree.ElementTree as ET
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    wf = root.find('workflow_parameters')
    
    params = {
        'input_user_or_path': wf.find('input_user_or_path').text,
        'input_database': wf.find('input_database').text,
        'input_backend': wf.find('input_backend').text if wf.find('input_backend') is not None else 'HDF5',
        'shot_nr': int(wf.find('shot_nr').text),
        'run_in': int(wf.find('run_in').text),
        'output_user_or_path': wf.find('output_user_or_path').text,
        'output_database': wf.find('output_database').text,
        'output_backend': wf.find('output_backend').text if wf.find('output_backend') is not None else 'HDF5',
        'run_out': int(wf.find('run_out').text),
        'tbegin': float(wf.find('tbegin').text) if wf.find('tbegin') is not None else -1.0,
        'tend': float(wf.find('tend').text) if wf.find('tend') is not None else -1.0,
        'dt_required': float(wf.find('dt_required').text) if wf.find('dt_required') is not None else 0.1,
        'one_time_slice': int(wf.find('one_time_slice').text) if wf.find('one_time_slice') is not None else 0,
    }
    
    return params


class WorkflowDriverM3Fortran:
    """
    MUSCLE3 Driver that directly communicates with Fortran torbeam_m3.exe
    
    Port structure (matching standalone Torbeam coupling.ymmsl):
    - O_I: equilibrium_out, core_profiles_out, ec_launchers_out
    - S: waves_in
    """
    
    def __init__(self, config_folder_path=None):
        print("[M3 Driver] Initializing (Fortran-compatible mode)...", file=sys.stdout)
        
        # Initialize steering to None (will be set by _load_ec_launchers if extra_cooking)
        self.steering = None
        
        # Create MUSCLE3 Instance with ports matching Fortran Torbeam
        ports = {
            Operator.O_I: ['equilibrium_out', 'core_profiles_out', 'ec_launchers_out'],
            Operator.S: ['waves_in']
        }
        
        try:
            self.instance = Instance(ports, KEEPS_NO_STATE_FOR_NEXT_USE)
            print("[M3 Driver] ✓ Instance created successfully", file=sys.stdout)
        except Exception as e:
            print(f"[M3 Driver] ✗ Failed to create Instance: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Read configuration path from MUSCLE3 settings
        try:
            self.config_path = self.instance.get_setting("config_folder_path", "str")
        except KeyError:
            if config_folder_path:
                self.config_path = os.path.abspath(config_folder_path)
            else:
                self.config_path = os.path.dirname(os.path.abspath(__file__))
                print(f"[M3 Driver] Warning: Using default config path: {self.config_path}", file=sys.stderr)
        
        print(f"[M3 Driver] Config path: {self.config_path}", file=sys.stdout)
        
        # Read extra_cooking setting (ITER-specific processing)
        try:
            self.extra_cooking = self.instance.get_setting("extra_cooking", "bool")
        except KeyError:
            self.extra_cooking = True  # Default for ITER
        
        print(f"[M3 Driver] extra_cooking: {self.extra_cooking}", file=sys.stdout)
        
        # Initialize environment
        self._initialize_environment()

    def _initialize_environment(self):
        """Initialize databases using IMAS API directly (bypassing WorkflowDbHelper)."""
        print("[M3 Driver] Setting up environment...", file=sys.stdout)
        
        # Load workflow parameters from XML
        inputworkflow_xml = os.path.join(self.config_path, "input_workflow.xml")
        print(f"[M3 Driver] Loading workflow config: {inputworkflow_xml}")
        
        if not os.path.exists(inputworkflow_xml):
            print(f"[M3 Driver] ERROR: {inputworkflow_xml} not found!", file=sys.stderr)
            sys.exit(1)
        
        try:
            params = parse_workflow_xml(inputworkflow_xml)
        except Exception as e:
            print(f"[M3 Driver] Error loading workflow XML: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Store parameters
        self.tbegin = params['tbegin']
        self.tend = params['tend']
        self.dt_required = params['dt_required']
        self.one_time_slice = params['one_time_slice']
        
        print(f"[M3 Driver] Input: {params['input_user_or_path']}/{params['input_database']}, shot={params['shot_nr']}, run={params['run_in']}")
        print(f"[M3 Driver] Output: {params['output_user_or_path']}/{params['output_database']}, run={params['run_out']}")
        print(f"[M3 Driver] Backend: {params['input_backend']}")
        
        # Initialize databases directly using IMAS API
        try:
            input_backend = get_backend_id(params['input_backend'])
            output_backend = get_backend_id(params['output_backend'])
            
            # Open input database with DD version 3 (to match standalone Torbeam)
            print(f"[M3 Driver] Opening input database (DD version 3)...")
            self.inputDb = imas.DBEntry(
                input_backend,
                params['input_database'],
                params['shot_nr'],
                params['run_in'],
                params['input_user_or_path'],
                data_version="3"  # Force DD 3 format
            )
            self.inputDb.open()
            print(f"[M3 Driver] ✓ Input database opened")
            
            # Determine output user/database
            output_user = params['output_user_or_path']
            if output_user == 'default':
                output_user = os.getenv('USER')
            output_database = params['output_database']
            if output_database == 'default':
                output_database = 'TORBEAM'
            
            # Create output database
            print(f"[M3 Driver] Creating output database: {output_user}/{output_database}")
            self.outputDb = imas.DBEntry(
                output_backend,
                output_database,
                params['shot_nr'],
                params['run_out'],
                output_user
            )
            self.outputDb.create()
            print(f"[M3 Driver] ✓ Output database created")
            
            # Create memory database for ec_launchers (also DD 3)
            print(f"[M3 Driver] Creating memory database...")
            self.md = imas.DBEntry(
                MEMORY_BACKEND,
                output_database,
                0,
                params['run_out'],
                output_user,
                data_version="3"  # Force DD 3 format
            )
            self.md.create()
            print(f"[M3 Driver] ✓ Memory database created")
            
        except Exception as e:
            print(f"[M3 Driver] ERROR: Failed to initialize databases: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # Load ec_launchers from YAML
        self._load_ec_launchers()
        
        print("[M3 Driver] Environment setup complete.", file=sys.stdout)

    def _load_ec_launchers(self):
        """
        Load ec_launchers using the same approach as standalone Torbeam.
        """
        if not isWaveformCookerPresent:
            print("[M3 Driver] ERROR: waveform_cooker not available!", file=sys.stderr)
            return
        
        # Look for ec_waveforms.yaml (preferred) or ec_launchers.yaml
        ec_waveforms_path = os.path.join(self.config_path, "ec_waveforms.yaml")
        ec_launchers_path = os.path.join(self.config_path, "ec_launchers.yaml")
        
        ec_launchers = None
        
        if os.path.exists(ec_waveforms_path):
            yaml_path = ec_waveforms_path
            print(f"[M3 Driver] Loading ec_launchers from: {yaml_path}", file=sys.stdout)
            
            if self.extra_cooking:
                print(f"[M3 Driver] Using ec_add_dynamic (extra_cooking=True)", file=sys.stdout)
                try:
                    ec_launchers, self.steering = ec_add_dynamic(yaml_path, kplot=0)
                    print(f"[M3 Driver] Steering config: {self.steering}", file=sys.stdout)
                except Exception as e:
                    print(f"[M3 Driver] ERROR in ec_add_dynamic: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    raise
            else:
                print(f"[M3 Driver] Using add_dynamic (extra_cooking=False)", file=sys.stdout)
                ec_launchers = add_dynamic(yaml_path, kplot=0)
                
        elif os.path.exists(ec_launchers_path):
            yaml_path = ec_launchers_path
            print(f"[M3 Driver] Loading ec_launchers from: {yaml_path}", file=sys.stdout)
            ec_launchers = add_dynamic(yaml_path, kplot=0)
            
        else:
            print(f"[M3 Driver] ERROR: No ec_waveforms.yaml or ec_launchers.yaml found in {self.config_path}", file=sys.stderr)
            print(f"[M3 Driver] Available files: {os.listdir(self.config_path)}", file=sys.stderr)
            sys.exit(1)
        
        if ec_launchers is not None:
            n_beams = len(ec_launchers.beam) if hasattr(ec_launchers, 'beam') else 0
            print(f"[M3 Driver] ec_launchers loaded: {n_beams} beams", file=sys.stdout)
            
            # Print beam info (first 3 beams)
            for i in range(min(3, n_beams)):
                beam = ec_launchers.beam[i]
                power = 0
                if hasattr(beam.power_launched, 'data') and len(beam.power_launched.data) > 0:
                    power = beam.power_launched.data[0]
                beam_name = beam.name if hasattr(beam, 'name') else f"beam_{i}"
                print(f"[M3 Driver]   beam[{i}]: {beam_name}, power={power/1e6:.3f} MW")
            if n_beams > 3:
                print(f"[M3 Driver]   ... and {n_beams - 3} more beams")
            
            # Store in memory database (critical for proper serialization!)
            self.md.put(ec_launchers)
            print(f"[M3 Driver] ec_launchers stored in memory DB", file=sys.stdout)

    def run(self):
        """
        Main workflow loop.
        """
        print("[M3 Driver] Starting main loop...", file=sys.stdout)
        
        # Determine time range from equilibrium
        try:
            eq_full = self.inputDb.get('equilibrium')
            time_array = eq_full.time
            print(f"[M3 Driver] Equilibrium time array: {time_array[:5]}... (len={len(time_array)})")
            if self.tbegin < 0:
                self.tbegin = time_array[0]
            if self.tend < 0:
                self.tend = time_array[-1]
        except Exception as e:
            print(f"[M3 Driver] Warning: Could not read time array: {e}", file=sys.stderr)
            if self.tbegin < 0:
                self.tbegin = 200.0
            if self.tend < 0:
                self.tend = 200.1
        
        if self.one_time_slice != 0:
            self.tend = self.tbegin + self.dt_required
        
        print(f"[M3 Driver] Time range: {self.tbegin:.3f} -> {self.tend:.3f} s, dt={self.dt_required:.3f}")
        
        # Get target DD version for conversion
        target_dd_version = os.getenv('IMAS_VERSION', '4.0.0')
        print(f"[M3 Driver] Target DD version for Fortran: {target_dd_version}")

        # MUSCLE3 main loop
        while self.instance.reuse_instance():
            timenow = self.tbegin
            step = 0
            
            while timenow < self.tend:
                step += 1
                t_next = timenow + self.dt_required
                
                print(f"\n{'='*60}")
                print(f"Step {step}: t={timenow:.4f} s")
                print(f"{'='*60}")
                
                # Read input data
                print("=> Read input IDSs")
                
                # Get equilibrium
                print("   ---> Get equilibrium")
                try:
                    # autoconvert=False ensures we get original data, then manually convert
                    input_equilibrium = self.inputDb.get_slice('equilibrium', timenow, 1, autoconvert=False)
                    
                    input_equilibrium = imas.convert_ids(input_equilibrium, target_dd_version)
                    
                    print(f"   equilibrium.time = {input_equilibrium.time}")
                except Exception as e:
                    print(f"   ERROR getting equilibrium: {e}", file=sys.stderr)
                    timenow = t_next
                    continue
                
                # Get core_profiles
                print("   ---> Get core_profiles")
                try:
                    input_core_profiles = self.inputDb.get_slice('core_profiles', timenow, 1, autoconvert=False)
                    
                    input_core_profiles = imas.convert_ids(input_core_profiles, target_dd_version)
                    
                    print(f"   core_profiles.time = {input_core_profiles.time}")
                except Exception as e:
                    print(f"   ERROR getting core_profiles: {e}", file=sys.stderr)
                    timenow = t_next
                    continue
                
                # Get ec_launchers from memory database
                print("   ---> Get ec_launchers")
                try:
                    input_ec_launchers = self.md.get_slice('ec_launchers', timenow, 3, autoconvert=False)
                    
                    input_ec_launchers = imas.convert_ids(input_ec_launchers, target_dd_version)
                    
                    input_ec_launchers.time = np.array([timenow])
                    
                    print(f"   ec_launchers.time = {input_ec_launchers.time}")
                except Exception as e:
                    print(f"   ERROR getting ec_launchers: {e}", file=sys.stderr)
                    timenow = t_next
                    continue
                
                # Apply ec_adjust if using extra_cooking with steering
                if self.extra_cooking and self.steering is not None:
                    print("   ---> Applying ec_adjust with steering")
                    input_ec_launchers = ec_adjust(input_ec_launchers, self.steering)
                
                # Print diagnostic info
                n_beams = len(input_ec_launchers.beam) if hasattr(input_ec_launchers, 'beam') else 0
                print(f"[M3 Driver] ec_launchers: {n_beams} beams")
                
                # Check total power
                total_power = 0.0
                for b in input_ec_launchers.beam:
                    if hasattr(b.power_launched, 'data') and len(b.power_launched.data) > 0:
                        total_power += b.power_launched.data[0]
                print(f"[M3 Driver] Total EC power: {total_power/1e6:.2f} MW")
                
                if total_power > 0:
                    # Send data to Torbeam Fortran executable
                    print("=> Execute TORBEAM")
                    
                    try:
                        # Send equilibrium
                        equilibrium_timestamp = float(input_equilibrium.time[-1])
                        equilibrium_data = input_equilibrium.serialize()
                        equilibrium_msg = Message(equilibrium_timestamp, data=equilibrium_data)
                        print(f"   Sending equilibrium_out (timestamp={equilibrium_timestamp}, size={len(equilibrium_data)} bytes)...")
                        self.instance.send("equilibrium_out", equilibrium_msg)
                        
                        # Send core_profiles
                        core_profiles_timestamp = float(input_core_profiles.time[-1])
                        core_profiles_data = input_core_profiles.serialize()
                        core_profiles_msg = Message(core_profiles_timestamp, data=core_profiles_data)
                        print(f"   Sending core_profiles_out (timestamp={core_profiles_timestamp}, size={len(core_profiles_data)} bytes)...")
                        self.instance.send("core_profiles_out", core_profiles_msg)
                        
                        # Send ec_launchers
                        # Note: time is already synced above in the [FIX] block
                        ec_launchers_timestamp = float(input_ec_launchers.time[-1])
                        ec_launchers_data = input_ec_launchers.serialize()
                        ec_launchers_msg = Message(ec_launchers_timestamp, data=ec_launchers_data)
                        print(f"   Sending ec_launchers_out (timestamp={ec_launchers_timestamp}, size={len(ec_launchers_data)} bytes)...")
                        self.instance.send("ec_launchers_out", ec_launchers_msg)
                        
                        # Receive waves output from Torbeam
                        print("   Waiting for waves_in...")
                        waves_msg = self.instance.receive("waves_in")
                        factory = imas.IDSFactory()
                        output_waves = factory.waves()
                        output_waves.deserialize(waves_msg.data)
                        waves_timestamp = waves_msg.timestamp
                        
                        print(f"[M3 Driver] ✓ Received waves output (time={waves_timestamp})")
                        
                        # Check if output has valid data and store results
                        has_valid_output = False
                        if USE_HAS_VALUE:
                            has_valid_output = output_waves.ids_properties.homogeneous_time.has_value
                        else:
                            from imas.imasdef import EMPTY_INT
                            has_valid_output = output_waves.ids_properties.homogeneous_time != EMPTY_INT
                        
                        if has_valid_output:
                            print("=> Export output IDSs to database")
                            self.outputDb.put_slice(output_waves)
                            self.outputDb.put_slice(input_equilibrium)
                            self.outputDb.put_slice(input_core_profiles)
                            self.outputDb.put_slice(input_ec_launchers)
                            print(f"   Output time = {output_waves.time[0]:.2f} s")
                        
                    except Exception as e:
                        print(f"[M3 Driver] ERROR during Torbeam execution: {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc()
                else:
                    print("   No power for this time slice, skipping Torbeam")
                
                timenow = t_next
        
        # Cleanup
        print("[M3 Driver] Closing databases...")
        self.inputDb.close()
        self.outputDb.close()
        self.md.close()
        print("[M3 Driver] Workflow finished.", file=sys.stdout)

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else None
    driver = WorkflowDriverM3Fortran(cfg_path)
    driver.run()