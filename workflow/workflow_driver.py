"""Database I/O and time loops for Legacy and Hybrid execution.

``hcd_nogui -c CONFIG`` runs iWrap actors directly. With ``--m3_flag=1``,
MUSCLE3 launches this driver as the macro and ``hcd_workflow_m3`` as the micro.
The Pure driver reuses the database and IDS helpers below.
"""

import inspect
import math
import os
import sys
import xml.etree.ElementTree as ET
from contextlib import ExitStack, contextmanager
from pathlib import Path

import imas
import numpy as np

import hcdworkflow
from gui.gui_methods import create_workflow_param_from_file
from hcdworkflow.hcd_workflow import HCDWorkflow
from hcdworkflow.workflow_dbhelper import WorkflowDbHelper
from hcdworkflow.workflow_globals_reader import WorkflowGlobalsReader

from workflow.ids_prep import (
    _create_ids,
    _get_target_dd_version,
    _smart_convert,
    get_backend,
    get_empty_int,
    stabilize_selected_hcd_outputs,
)

isWaveformCookerPresent = True
try:
    from waveform_cooker import add_dynamic
except Exception:
    isWaveformCookerPresent = False


def _waveform_ids_name(file_path):
    try:
        import yaml
    except Exception:
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as file_obj:
            data = yaml.safe_load(file_obj)
        return data.get("ids") if isinstance(data, dict) else None
    except Exception:
        return None


@contextmanager
def _waveform_cooker_imas2_open_compat():
    """Adapt Waveform-Cooker's legacy DBEntry.open() expectation for IMASPy 2."""
    if not hasattr(imas, "IDSFactory"):
        yield
        return

    original_dbentry = imas.DBEntry
    original_open = original_dbentry.open
    original_structure_setattr = None
    ids_structure_cls = None
    added_imasdef_alias = False

    if not hasattr(imas, "imasdef") and hasattr(imas, "ids_defs"):
        imas.imasdef = imas.ids_defs
        added_imasdef_alias = True

    def _dd_version_compat(data_version):
        text = str(data_version)
        if "." in text:
            return text
        if text == "3":
            return "3.41.0"
        if text == "4":
            return _get_target_dd_version()
        return text

    def _dbentry_compat(*args, **kwargs):
        data_version = kwargs.get("data_version")
        if data_version is not None and "dd_version" not in kwargs:
            kwargs["dd_version"] = _dd_version_compat(data_version)
        return original_dbentry(*args, **kwargs)

    def _open_with_status(db_entry, *args, **kwargs):
        result = original_open(db_entry, *args, **kwargs)
        if result is None:
            return 0, None
        return result

    try:
        from imas.ids_structure import IDSStructure

        ids_structure_cls = IDSStructure
        original_structure_setattr = IDSStructure.__setattr__

        def _setattr_compat(self, key, value):
            try:
                return original_structure_setattr(self, key, value)
            except AttributeError as exc:
                if key == "time" and "has no attribute 'time'" in str(exc):
                    return None
                raise

        IDSStructure.__setattr__ = _setattr_compat
    except Exception:
        pass

    original_dbentry.open = _open_with_status
    imas.DBEntry = _dbentry_compat
    try:
        yield
    finally:
        imas.DBEntry = original_dbentry
        original_dbentry.open = original_open
        if ids_structure_cls is not None and original_structure_setattr is not None:
            ids_structure_cls.__setattr__ = original_structure_setattr
        if added_imasdef_alias:
            delattr(imas, "imasdef")


# =============================================================================
# DB Read Helpers (whole-IDS reads with smart DD conversion)
# =============================================================================


def _read_ids(db_entry, ids_name, *args):
    """Disable automatic conversion only with the modern IMAS-Python API."""
    options = {"autoconvert": False} if hasattr(imas, "IDSFactory") else {}
    return db_entry.get(ids_name, *args, **options)


def _read_ids_slice(db_entry, ids_name, timenow):
    options = {"autoconvert": False} if hasattr(imas, "IDSFactory") else {}
    return db_entry.get_slice(ids_name, timenow, 1, **options)


def safe_get_ids(db_entry, ids_name):
    """Safely get an IDS from database, with smart DD conversion."""
    try:
        ids_object = _read_ids(db_entry, ids_name)
        ids_object = _smart_convert(ids_object, ids_name)
        if hasattr(ids_object, "ids_properties"):
            homogeneous_time = getattr(ids_object.ids_properties, "homogeneous_time", None)
            if homogeneous_time is not None and homogeneous_time != get_empty_int():
                return ids_object, True
        return ids_object, False
    except Exception as e:
        error_msg = str(e).lower()
        if "empty" in error_msg or "not found" in error_msg or "does not exist" in error_msg:
            print(f"  IDS '{ids_name}' is empty or not found, skipping.")
            return None, False
        else:
            raise


def _safe_partial_get(db_entry, ids_name: str, data_path: str, occurrence: int = 0):
    """Safely get a partial IDS field from a database entry."""
    try:
        if hasattr(db_entry, "partial_get"):
            return db_entry.partial_get(ids_name=ids_name, data_path=data_path, occurrence=occurrence)
        else:
            try:
                ids_object = _read_ids(db_entry, ids_name, occurrence)
                ids_object = _smart_convert(ids_object, ids_name)
                result = ids_object
                for part in data_path.split("/"):
                    if part:
                        result = getattr(result, part)
                return result
            except Exception as e:
                if "empty" in str(e).lower():
                    return None
                raise
    except Exception as e:
        print(f"  ERROR in _safe_partial_get({ids_name}, {data_path}): {e}")
        return None


# =============================================================================
# M3 Port Definitions (only used in m3_flag=1 mode)
# =============================================================================

# Ports that send IDS from macro to micro (O_I → F_INIT)
SEND_PORTS = [
    "equilibrium_out",
    "core_profiles_out",
    "workflow_out",
    "ec_launchers_out",
    "ic_antennas_out",
    "core_sources_out",
    "distributions_out",
    "distribution_sources_out",
    "nbi_out",
    "wall_out",
]

# Ports that receive IDS from micro to macro (O_F → S)
RECV_PORTS = [
    "core_sources_in",
    "waves_in",
    "core_profiles_in",
    "distributions_in",
    "distribution_sources_in",
]


def _port_to_ids(port_name):
    """Convert port name to IDS name: 'equilibrium_out' → 'equilibrium'."""
    return port_name.rsplit("_", 1)[0]


def _serialize_m3_input(ids_data, ids_name):
    """Represent absent optional inputs explicitly; propagate corrupt payloads."""
    if ids_data is None or int(ids_data.ids_properties.homogeneous_time) < 0:
        ids_data = _create_ids(ids_name)
        # The executor recognizes homogeneous_time=0 as an empty input and
        # supplies the current time when the selected actor needs it.
        ids_data.ids_properties.homogeneous_time = 0
    try:
        return ids_data.serialize()
    except Exception as error:
        raise RuntimeError(f"Could not serialize {ids_name}: {error}") from error


def _deserialize_m3_output(message, ids_name, timenow):
    """Accept only a decodable response for the current controller time."""
    if not math.isfinite(message.timestamp) or not math.isclose(
        message.timestamp, timenow, rel_tol=0.0, abs_tol=1.0e-9
    ):
        raise RuntimeError(f"Unexpected timestamp for {ids_name}: {message.timestamp}, expected {timenow}")
    ids_obj = _create_ids(ids_name)
    if message.data is not None and len(message.data) > 0:
        try:
            ids_obj.deserialize(message.data)
        except Exception as error:
            raise RuntimeError(f"Could not deserialize {ids_name}: {error}") from error
        if int(ids_obj.ids_properties.homogeneous_time) >= 0 and hasattr(ids_obj, "time"):
            ids_obj.time = np.array([timenow])
    return ids_obj


# =============================================================================
# Database Setup (shared by both modes)
# =============================================================================


def setup_databases(config_folder_path):
    """Initialize all databases and load machine descriptions.

    Return the input, output and machine database handles, input IDS names,
    machine-description IDS names, workflow parameters and process selection.
    """
    pathGlobalConfiguration = Path(inspect.getfile(hcdworkflow)).parent / "global_configuration"
    globalListPath = str(pathGlobalConfiguration / "global_lists.yaml")

    # Load workflow parameters from XML
    inputworkflow_xml = os.path.join(config_folder_path, "input_workflow.xml")
    print(f"[workflow_driver] Loading config from: {inputworkflow_xml}")
    wf_parameters = create_workflow_param_from_file(inputworkflow_xml)["workflow_parameters"][0]
    param_process = {
        node.tag: int(node.text) for node in ET.parse(inputworkflow_xml).findall("./actor_selection/*/*/*")
    }

    # Extract database parameters
    input_user_or_path = wf_parameters["input_user_or_path"][0]
    input_database = wf_parameters["input_database"][0]
    input_backend = wf_parameters["input_backend"][0]
    ddv_backend = wf_parameters["ddv_backend"][0] if "ddv_backend" in wf_parameters else _get_target_dd_version()
    output_user_or_path = wf_parameters["output_user_or_path"][0]
    output_database = wf_parameters["output_database"][0]
    output_backend = wf_parameters.get("output_backend", ["HDF5"])[0]
    shot_nr = wf_parameters["shot_nr"][0]
    run_in = wf_parameters["run_in"][0]
    run_out = wf_parameters["run_out"][0]

    print("[workflow_driver] Opening input and output databases...")

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
    with ExitStack() as cleanup:
        inputDb = dbhelper.getInputDatabase()
        cleanup.callback(inputDb.close)
        outputDb = dbhelper.getOutputDatabase()
        cleanup.callback(outputDb.close)
        machineDb = dbhelper.getMachineDatabase()
        cleanup.callback(machineDb.close)

        # Load global lists
        globallistReader = WorkflowGlobalsReader(globalListPath)
        inputIds = globallistReader.getIdsScenarioList()
        inputIds.append("workflow")
        inputMds = globallistReader.getIdsMdList()
        wall_md = globallistReader.getWallMD()

        # Load machine descriptions
        print("[workflow_driver] Loading machine descriptions...")
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
                        try:
                            wall.open()
                            wall_ids, wall_valid = safe_get_ids(wall, "wall")
                            if wall_valid and wall_ids is not None:
                                machineDb.put(wall_ids)
                            else:
                                print("  wall IDS is empty in MD database --> running without.")
                        finally:
                            wall.close()
                    except Exception as e:
                        print(f"  wall IDS not found --> running without. Error: {e}")
                else:
                    print(f"  {idsName} not present, can be provided via waveform cooker if needed.")

        # Load waveform configurations
        print("[workflow_driver] Loading waveform configurations...")
        for filename in os.listdir(config_folder_path):
            filePath = os.path.join(config_folder_path, filename)
            if filePath.endswith("waveforms.yaml"):
                if isWaveformCookerPresent:
                    with _waveform_cooker_imas2_open_compat():
                        idsObject = add_dynamic(filePath)
                else:
                    idsObject = None
                if idsObject is not None:
                    ids_name = _waveform_ids_name(filePath)
                    if ids_name:
                        idsObject = _smart_convert(idsObject, ids_name)
                    machineDb.put(idsObject)

        cleanup.pop_all()
        return inputDb, outputDb, machineDb, inputIds, inputMds, wf_parameters, param_process


# =============================================================================
# Database I/O Helpers
# =============================================================================


def get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow):
    """Read all IDS slices at the given time, with smart DD conversion."""
    slices = {}
    for ids_name in inputIds:
        try:
            ids_obj = _read_ids_slice(inputDb, ids_name, timenow)
            slices[ids_name] = _smart_convert(ids_obj, ids_name)
            if (
                ids_name in {"equilibrium", "core_profiles"}
                and int(slices[ids_name].ids_properties.homogeneous_time) < 0
            ):
                raise ValueError(f"Required IDS {ids_name} is empty")
        except Exception as e:
            if ids_name not in {"equilibrium", "core_profiles"} and "empty" in str(e).lower():
                slices[ids_name] = _create_ids(ids_name)
            else:
                raise RuntimeError(f"Could not read {ids_name} at t={timenow}: {e}") from e
    for ids_name in inputMds:
        try:
            ids_obj = _read_ids_slice(machineDb, ids_name, timenow)
            slices[ids_name] = _smart_convert(ids_obj, ids_name)
        except Exception as e:
            if not any(text in str(e).lower() for text in ("empty", "not found", "does not exist")):
                raise RuntimeError(f"Could not read {ids_name} at t={timenow}: {e}") from e
    return slices


_OUTPUT_OWNED_IDS = {
    "core_profiles",
    "core_sources",
    "waves",
    "distributions",
    "distribution_sources",
}


def _valid_output_slice(ids_data):
    return (
        ids_data is not None
        and hasattr(ids_data, "ids_properties")
        and int(ids_data.ids_properties.homogeneous_time) >= 0
        and hasattr(ids_data, "time")
        and len(ids_data.time) > 0
        and ids_data.time[0] > 0
    )


def store_ids_slices(
    outputDb, inputMds, input_slices, output_ids, m3_flag=0, param_process=None, timenow=None, config_folder_path=None
):
    """Write IDS slices to the output database.

    Write each IDS once per slice. Preserve the input core_profiles when no
    actor produces a valid replacement; writing both versions at the same time
    corrupts the HDF5 group index on subsequent put_slice calls.
    """
    stabilize_selected_hcd_outputs(
        input_slices,
        output_ids,
        param_process,
        timenow,
        config_folder_path=config_folder_path,
    )

    for ids_name, ids_data in input_slices.items():
        if ids_name in inputMds:
            continue
        if ids_name in _OUTPUT_OWNED_IDS:
            if ids_name != "core_profiles" or _valid_output_slice(output_ids.get(ids_name)):
                continue
        if hasattr(ids_data, "ids_properties") and ids_data.ids_properties.homogeneous_time >= 0:
            if ids_data.ids_properties.homogeneous_time == 2:
                outputDb.put(ids_data)
            else:
                outputDb.put_slice(ids_data)

    for ids_name, ids_data in output_ids.items():
        if _valid_output_slice(ids_data):
            if ids_name != "equilibrium":
                # Skip empty core_sources (no source data) to avoid HDF5 schema
                # conflict: writing an empty core_sources first establishes an
                # HDF5 schema without source arrays, causing subsequent put_slice
                # with populated source data to segfault.
                if ids_name == "core_sources" and (not hasattr(ids_data, "source") or len(ids_data.source) == 0):
                    continue
                print(f"  -> Storing output {ids_name} at t={ids_data.time[0]:.4f}", flush=True)
                if m3_flag == 1:
                    clean_ids = _create_ids(ids_name)
                    clean_ids.deserialize(ids_data.serialize())
                    outputDb.put_slice(clean_ids)
                else:
                    outputDb.put_slice(ids_data)
                print(f"  -> Stored output {ids_name} at t={ids_data.time[0]:.4f}", flush=True)


# =============================================================================
# Time Range Resolution (shared by both modes)
# =============================================================================


def resolve_time_range(workflow, inputDb):
    """
    Resolve the time range from workflow config and database.
    Returns: (tbegin, tend, dt, nsteps, one_time_slice)
    """
    tbegin = workflow.workflowData.tbegin
    tend = workflow.workflowData.tend
    dt = workflow.workflowData.dt_required
    one_time_slice = workflow.workflowData.one_time_slice

    if one_time_slice == 0:
        time_array = _safe_partial_get(inputDb, "equilibrium", "time")
        if time_array is not None:
            if tbegin < 0:
                tbegin = time_array[0]
            if tend < 0:
                tend = time_array[-1]
    else:
        tend = tbegin + dt

    nsteps = 1 if one_time_slice else int((tend - tbegin) / dt)
    if dt * nsteps < (tend - tbegin):
        nsteps += 1

    return tbegin, tend, dt, nsteps, one_time_slice


# =============================================================================
# Mode 0: Traditional iwrap
# =============================================================================


def run_traditional(
    config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds, param_process, *, workflow=None
):
    """
    Run in traditional mode: time loop + HCDWorkflow.run() directly.
    No MUSCLE3 involvement. All iWrap actors execute in-process.
    """
    if workflow is None:
        print("[workflow_driver] Initializing HCDWorkflow (traditional mode)...", flush=True)
        workflow = HCDWorkflow()
        workflow.initialize(config_folder_path)

    tbegin, tend, dt, nsteps, one_time_slice = resolve_time_range(workflow, inputDb)
    print(f"[workflow_driver] Time range: {tbegin} → {tend}, dt={dt}, steps={nsteps}", flush=True)

    # --- Time loop ---
    timenow = tbegin
    step = 0

    while timenow < tend:
        step += 1
        print("---------------------------------------------", flush=True)
        print(f"[workflow_driver] Step {step}/{nsteps}, t={timenow:.4f}, dt={dt:.4f}", flush=True)

        # Read IDS from database
        ids_slices = get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow)
        # Separate mandatory and optional IDS
        nonmandatory = {k: v for k, v in ids_slices.items() if k not in ("equilibrium", "core_profiles", "workflow")}

        # Set process status and run
        workflow.setProcessStatus(timenow)
        output_ids = workflow.run(
            equilibrium=ids_slices["equilibrium"],
            core_profiles=ids_slices["core_profiles"],
            workflow=ids_slices["workflow"],
            **nonmandatory,
        )
        if output_ids is None:
            raise RuntimeError(f"HCD workflow failed at t={timenow}")

        # Store results
        store_ids_slices(
            outputDb,
            inputMds,
            ids_slices,
            output_ids,
            m3_flag=0,
            param_process=param_process,
            timenow=timenow,
            config_folder_path=config_folder_path,
        )

        timenow += dt

    print(f"[workflow_driver] Finished after {step} steps", flush=True)


# =============================================================================
# Mode 1: MUSCLE3 Hybrid (Macro Model)
# =============================================================================


def run_m3_macro(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds, param_process):
    """
    Run as MUSCLE3 macro model.
    Manages: time loop, database I/O, M3 send/receive.
    HCDWorkflow.run() happens in the micro model (hcd_workflow_m3.py).
    """
    from libmuscle import Instance, Message, InstanceFlags
    from ymmsl import Operator

    # --- Create MUSCLE3 Instance ---
    ports = {
        Operator.O_I: SEND_PORTS,
        Operator.S: RECV_PORTS,
    }
    instance = Instance(ports, InstanceFlags.SKIP_MMSF_SEQUENCE_CHECKS)

    print("[workflow_driver] M3 macro instance created", flush=True)
    print(f"  O_I (send → micro): {SEND_PORTS}", flush=True)
    print(f"  S   (recv ← micro): {RECV_PORTS}", flush=True)

    # --- Resolve time range ---
    wf_config = HCDWorkflow()
    wf_config.initialize(config_folder_path)
    tbegin, tend, dt, nsteps, one_time_slice = resolve_time_range(wf_config, inputDb)
    print(f"[workflow_driver] Time range: {tbegin} → {tend}, dt={dt}, steps={nsteps}", flush=True)

    # --- Determine connected ports ---
    connected_send = [p for p in SEND_PORTS if instance.is_connected(p)]
    connected_recv = [p for p in RECV_PORTS if instance.is_connected(p)]
    print(f"[workflow_driver] Connected send ports: {connected_send}", flush=True)
    print(f"[workflow_driver] Connected recv ports: {connected_recv}", flush=True)

    # --- Time loop inside single reuse ---
    # MMSF pattern: macro's ONE reuse contains the entire time loop.
    # Each O_I/S pair inside the loop triggers one micro reuse_instance().
    # When macro exits the loop, micro's reuse_instance() returns False.
    timenow = tbegin
    step = 0

    while instance.reuse_instance():
        # All timesteps run inside this single reuse
        while timenow < tend:
            step += 1
            t_next = timenow + dt
            if t_next > tend:
                t_next = None  # last step

            print("---------------------------------------------", flush=True)
            print(f"[workflow_driver] Step {step}/{nsteps}, t={timenow:.4f}, dt={dt:.4f}", flush=True)

            # --- Read IDS from database ---
            ids_slices = get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow)
            # --- O_I: Send IDS to hcd_workflow ---
            for port_name in connected_send:
                ids_name = _port_to_ids(port_name)
                ids_data = ids_slices.get(ids_name)

                serialized = _serialize_m3_input(ids_data, ids_name)

                print(f"  -> Sending {ids_name} on {port_name} ({len(serialized)} bytes)", flush=True)
                instance.send(port_name, Message(timenow, t_next, data=serialized))

            # --- S: Receive updated IDS from hcd_workflow ---
            output_ids = {}
            for port_name in connected_recv:
                ids_name = _port_to_ids(port_name)
                print(f"  <- Waiting for {ids_name} on {port_name}...", flush=True)
                msg = instance.receive(port_name)

                output_ids[ids_name] = _deserialize_m3_output(msg, ids_name, timenow)
                print(f"  <- Received {ids_name} (t={msg.timestamp:.4f})", flush=True)

            # --- Store results to database ---
            store_ids_slices(
                outputDb,
                inputMds,
                ids_slices,
                output_ids,
                m3_flag=1,
                param_process=param_process,
                timenow=timenow,
                config_folder_path=config_folder_path,
            )

            timenow += dt

    print(f"[workflow_driver] Finished after {step} steps", flush=True)


# =============================================================================
# Entry Point
# =============================================================================


def workflow_driver(par_path, m3_flag=0):
    """
    Main workflow driver function.

    Args:
        par_path: Path to the configuration folder containing input_workflow.xml
        m3_flag: Execution mode
            - 0: Traditional mode (HCDWorkflow.run() in-process)
            - 1: MUSCLE3 macro (sends IDS to hcd_workflow micro via M3)
    """
    print("=" * 60, flush=True)
    print("[workflow_driver] Starting HCD Workflow", flush=True)
    print(f"[workflow_driver] Mode: {'MUSCLE3 Macro' if m3_flag == 1 else 'Traditional iwrap'}", flush=True)
    print(f"[workflow_driver] Config path: {par_path}", flush=True)
    print("=" * 60, flush=True)

    config_folder_path = os.path.abspath(par_path)

    # Database setup is the same for both modes
    inputDb, outputDb, machineDb, inputIds, inputMds, wf_parameters, param_process = setup_databases(config_folder_path)

    with ExitStack() as cleanup:
        for database in (inputDb, outputDb, machineDb):
            cleanup.callback(database.close)
        # Dispatch based on mode
        if m3_flag == 1:
            run_m3_macro(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds, param_process)
        else:
            run_traditional(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds, param_process)

    print("=" * 60)
    print("[workflow_driver] Workflow completed successfully")
    print("=" * 60)


wf_wrapper = workflow_driver


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python workflow_driver.py <config_path> [m3_flag]")
        print("  config_path: Path to configuration folder")
        print("  m3_flag: 0=traditional iwrap, 1=MUSCLE3 macro (default: 0)")
        sys.exit(1)

    config_path = sys.argv[1]
    m3_flag = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    workflow_driver(config_path, m3_flag=m3_flag)
