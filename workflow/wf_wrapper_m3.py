"""
Workflow Wrapper with MUSCLE3 Support

This is the top-level entry point for the HCD workflow.

Architecture:
    wf_wrapper_m3.py (this file)
        └── WorkflowDriver (workflow_driver_m3.py)
                ├── m3_flag=0: Uses original HCDWorkflow directly
                └── m3_flag=1: Handles M3 communication, then calls original HCDWorkflow
                        └── HCDWorkflow (original, unchanged)
                                └── WorkflowExecutor (original, unchanged)

Usage:
    # Traditional mode (all actors in-process)
    python wf_wrapper_m3.py /path/to/config 0
    
    # Hybrid M3 mode (external actors via MUSCLE3)
    python wf_wrapper_m3.py /path/to/config 1

Note:
    In M3 mode (m3_flag=1), this script should be launched by MUSCLE3 Manager
    as the 'hcd_workflow' component in the ymmsl configuration.
"""

import inspect
import os
import sys
from pathlib import Path

import imas

import hcdworkflow
from gui.gui_methods import create_workflow_param_from_file
from hcdworkflow.workflow_dbhelper import WorkflowDbHelper
from hcdworkflow.workflow_globals_reader import WorkflowGlobalsReader

# Import WorkflowDriver (handles both traditional and M3 modes)
from hcdworkflow.workflow_driver_m3 import WorkflowDriver

isWaveformCookerPresent = True
try:
    from waveform_cooker import add_dynamic
except Exception as _:
    isWaveformCookerPresent = False


# =============================================================================
# IMAS API Compatibility Layer
# =============================================================================

def get_empty_int():
    """Get the EMPTY_INT constant, compatible with both IMAS APIs."""
    if hasattr(imas, 'ids_defs'):
        return imas.ids_defs.EMPTY_INT
    elif hasattr(imas, 'imasdef'):
        return imas.imasdef.EMPTY_INT
    else:
        return -999999999


def get_backend(backend_name: str):
    """Get backend constant, compatible with both IMAS APIs."""
    backend_attr = f"{backend_name}_BACKEND"
    if hasattr(imas, 'ids_defs'):
        return getattr(imas.ids_defs, backend_attr)
    elif hasattr(imas, 'imasdef'):
        return getattr(imas.imasdef, backend_attr)
    else:
        raise RuntimeError(f"Cannot find IMAS backend definitions")


def safe_get_ids(db_entry, ids_name):
    """Safely get an IDS from database, handling empty/missing cases."""
    try:
        ids_object = db_entry.get(ids_name)
        if hasattr(ids_object, 'ids_properties'):
            homogeneous_time = getattr(ids_object.ids_properties, 'homogeneous_time', None)
            if homogeneous_time is not None and homogeneous_time != get_empty_int():
                return ids_object, True
        return ids_object, False
    except Exception as e:
        error_msg = str(e).lower()
        if 'empty' in error_msg or 'not found' in error_msg or 'does not exist' in error_msg:
            print(f"  IDS '{ids_name}' is empty or not found, skipping.")
            return None, False
        else:
            raise


def wf_wrapper(par_path, m3_flag=0):
    """
    Main workflow wrapper function.
    
    Args:
        par_path: Path to the configuration folder containing input_workflow.xml
        m3_flag: Execution mode
            - 0: Traditional mode (actors called in-process via iwrap)
            - 1: Hybrid M3 mode (actors called via MUSCLE3)
    """
    print("=" * 60, flush=True)
    print(f"[wf_wrapper] Starting HCD Workflow", flush=True)
    print(f"[wf_wrapper] Mode: {'MUSCLE3 Hybrid' if m3_flag == 1 else 'Traditional iwrap'}", flush=True)
    print(f"[wf_wrapper] Config path: {par_path}", flush=True)
    print("=" * 60, flush=True)
    
    config_folder_path = os.path.abspath(par_path)

    pathGlobalConfiguration = Path(inspect.getfile(hcdworkflow)).parent / "global_configuration"
    globalListPath = str(pathGlobalConfiguration / "global_lists.yaml")

    # Load workflow parameters from XML
    inputworkflow_xml = os.path.join(config_folder_path, "input_workflow.xml")
    print(f"[wf_wrapper] Loading config from: {inputworkflow_xml}")
    wf_parameters = create_workflow_param_from_file(inputworkflow_xml)["workflow_parameters"][0]

    # Extract database parameters
    input_user_or_path = wf_parameters["input_user_or_path"][0]
    input_database = wf_parameters["input_database"][0]
    input_backend = wf_parameters["input_backend"][0]
    ddv_backend = wf_parameters["ddv_backend"][0]
    output_user_or_path = wf_parameters["output_user_or_path"][0]
    output_database = wf_parameters["output_database"][0]
    output_backend = wf_parameters.get("output_backend", ["HDF5"])[0]
    shot_nr = wf_parameters["shot_nr"][0]
    run_in = wf_parameters["run_in"][0]
    run_out = wf_parameters["run_out"][0]

    print("[wf_wrapper] Opening input and output databases...")

    # Initialize database helper
    dbhelper = WorkflowDbHelper(
        input_user_or_path,
        input_database,
        input_backend,
        ddv_backend,
        output_user_or_path,
        output_database,
        output_backend,
        shot_nr,
        run_in,
        run_out,
    )
    inputDb = dbhelper.getInputDatabase()
    outputDb = dbhelper.getOutputDatabase()
    machineDb = dbhelper.getMachineDatabase()

    # Load global lists
    globallistReader = WorkflowGlobalsReader(globalListPath)
    inputIds = globallistReader.getIdsScenarioList()
    inputIds.append("workflow")
    inputMds = globallistReader.getIdsMdList()
    wall_md = globallistReader.getWallMD()

    # Load machine descriptions
    print("[wf_wrapper] Loading machine descriptions...")
    for idsName in inputMds:
        idsObject, is_valid = safe_get_ids(inputDb, idsName)
        
        if is_valid and idsObject is not None:
            machineDb.put(idsObject)
        else:
            if idsName == "wall":
                try:
                    _backend = get_backend(wall_md["backend"])
                    wall = imas.DBEntry(
                        _backend,
                        wall_md["database"],
                        wall_md["shot"],
                        wall_md["run"],
                        wall_md["user_or_path"],
                    )
                    wall.open()
                    wall_ids, wall_valid = safe_get_ids(wall, "wall")
                    if wall_valid and wall_ids is not None:
                        machineDb.put(wall_ids)
                    else:
                        print("  wall IDS is empty in MD database --> running without.")
                except Exception as e:
                    print(f"  wall IDS not found --> running without. Error: {e}")
            else:
                print(f"  {idsName} not present, can be provided via waveform cooker if needed.")

    # Load waveform configurations
    print("[wf_wrapper] Loading waveform configurations...")
    for filename in os.listdir(config_folder_path):
        filePath = os.path.join(config_folder_path, filename)
        if filePath.endswith("waveforms.yaml"):
            if os.path.exists(filePath):
                idsObject = add_dynamic(filePath) if isWaveformCookerPresent else None
            if idsObject is not None:
                machineDb.put(idsObject)

    # =========================================================================
    # Create and run WorkflowDriver
    # - m3_flag=0: Traditional mode, WorkflowDriver uses original HCDWorkflow
    # - m3_flag=1: M3 mode, WorkflowDriver handles M3 communication
    # =========================================================================
    print("[wf_wrapper] Creating WorkflowDriver...")
    workflowWrapper = WorkflowDriver(config_folder_path, m3_flag=m3_flag)
    workflowWrapper.initialize(inputDb, outputDb, machineDb, inputIds, inputMds)

    print("[wf_wrapper] Starting time loop execution...")
    workflowWrapper.executeTimeloop()

    # Cleanup
    print("[wf_wrapper] Closing databases...")
    inputDb.close()
    outputDb.close()
    machineDb.close()

    print("=" * 60)
    print("[wf_wrapper] Workflow completed successfully")
    print("=" * 60)


def wf_wrapper_m3(par_path):
    """
    Convenience function to run workflow in MUSCLE3 hybrid mode.
    Equivalent to: wf_wrapper(par_path, m3_flag=1)
    """
    return wf_wrapper(par_path, m3_flag=1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wf_wrapper_m3.py <config_path> [m3_flag]")
        print("  config_path: Path to configuration folder")
        print("  m3_flag: 0=traditional iwrap, 1=MUSCLE3 hybrid (default: 0)")
        sys.exit(1)
    
    config_path = sys.argv[1]
    m3_flag = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    
    wf_wrapper(config_path, m3_flag=m3_flag)