"""
wf_wrapper_m3.py — Unified HCD Workflow Entry Point

This file is the single top-level entry point for the HCD workflow,
handling both traditional (iwrap) and MUSCLE3 hybrid execution modes.

Architecture:
    m3_flag=0 (Traditional):
        wf_wrapper_m3.py (this file)
            ├── Database I/O
            ├── Time loop
            └── HCDWorkflow.run() directly (iWrap actors in-process)

    m3_flag=1 (MUSCLE3 Hybrid, this file = macro model):
        wf_wrapper_m3.py (this file, MUSCLE3 macro)
            ├── Database I/O
            ├── Time loop (timestep-level reuse)
            └── M3 send/receive IDS ↔ hcd_workflow_m3.py

        hcd_workflow_m3.py (MUSCLE3 micro, separate process)
            └── HCDWorkflow.run() with iWrap actors (invisible to M3)

Usage:
    # Traditional mode (all actors in-process)
    python wf_wrapper_m3.py /path/to/config 0

    # Hybrid M3 mode (launched by MUSCLE3 Manager)
    python wf_wrapper_m3.py /path/to/config 1
"""

import inspect
import os
import sys
import copy
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import numpy as np
import imas

try:
    from scipy.ndimage import gaussian_filter
except ImportError:
    gaussian_filter = None

import hcdworkflow
from gui.gui_methods import create_workflow_param_from_file
from hcdworkflow.hcd_workflow import HCDWorkflow
from hcdworkflow.workflow_dbhelper import WorkflowDbHelper
from hcdworkflow.workflow_globals_reader import WorkflowGlobalsReader

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


def _get_target_dd_version():
    """Get the DD version of the current IMAS environment."""
    return os.getenv('IMAS_VERSION', imas.dd_zip.dd_xml_versions()[-1])


def _smart_convert(ids_object, ids_name):
    """Convert IDS to target DD version if needed, with manual fix-ups.

    Follows the Torbeam standalone pattern:
      1. autoconvert=False by default
      2. Check DD version mismatch
      3. Convert only if needed via imas.convert_ids()
      4. Apply manual fix-ups for fields that don't convert cleanly

    IMPORTANT: For equilibrium, fix-ups are applied unconditionally
    (not only after DD conversion), because issues like missing b_field,
    NaN values, and missing triangularity_lower exist regardless of DD version.

    Returns the (possibly converted) IDS object.
    """
    target_dd = _get_target_dd_version()
    source_dd = getattr(ids_object.ids_properties.version_put, 'data_dictionary', '')

    if source_dd and source_dd != target_dd:
        print(f"  [{ids_name}] Converting DD {source_dd} → {target_dd}", flush=True)

        # Capture fields that will be lost during conversion
        pre_convert_data = {}
        if ids_name == 'ec_launchers':
            pre_convert_data = _capture_ec_launchers_fields(ids_object)

        ids_object = imas.convert_ids(ids_object, target_dd)

        # --- Manual fix-ups after conversion ---
        if ids_name == 'ec_launchers':
            ids_object = _fixup_ec_launchers(ids_object, pre_convert_data)

    # --- Unconditional fix-ups (run regardless of DD version match) ---
    if ids_name == 'equilibrium':
        ids_object = _fixup_equilibrium(ids_object)

    return ids_object


def _capture_ec_launchers_fields(ec):
    """Capture ec_launchers fields that are lost during DD conversion.

    In DD 3.x: beam.mode (int) and beam.o_mode_fraction (1D array)
    In DD 4.1.0: beam.polarization.o_mode_fraction (1D array)
    """
    data = {}
    for i, beam in enumerate(ec.beam):
        beam_data = {}
        if hasattr(beam, 'o_mode_fraction') and beam.o_mode_fraction.has_value:
            beam_data['o_mode_fraction'] = np.array(beam.o_mode_fraction)
        elif hasattr(beam, 'mode'):
            # mode=1 means O-mode, mode=0 or -1 means X-mode
            try:
                mode_val = int(beam.mode)
                beam_data['o_mode_fraction'] = np.array([1.0 if mode_val == 1 else 0.0])
            except Exception:
                pass
        data[i] = beam_data
    return data


def _fixup_ec_launchers(ec, pre_convert_data):
    """Apply manual fix-ups for ec_launchers IDS after DD conversion.

    Restores o_mode_fraction from pre-conversion data into the new
    beam.polarization.o_mode_fraction location.
    """
    for i, beam in enumerate(ec.beam):
        if i in pre_convert_data and 'o_mode_fraction' in pre_convert_data[i]:
            if hasattr(beam, 'polarization'):
                p = beam.polarization
                if not p.o_mode_fraction.has_value:
                    old_val = pre_convert_data[i]['o_mode_fraction']
                    p.o_mode_fraction = old_val
    if pre_convert_data:
        print(f"  [ec_launchers] Restored o_mode_fraction for {len(pre_convert_data)} beams", flush=True)
    return ec


def _fixup_equilibrium(eq):
    """Apply manual fix-ups for equilibrium IDS.

    This runs UNCONDITIONALLY (not only after DD conversion) because
    these issues exist in the source data regardless of DD version:
      - Missing b_field_r/z/phi computation from psi
      - NaN values in 2D profiles
      - b_field_tor → b_field_phi renaming (DD 3.42 legacy)
      - Missing vacuum toroidal field quantities
      - Missing triangularity_lower (needed by Cyrano)

    Reference: Torbeam standalone run_torbeam script,
               Cyrano standalone run_cyrano script.
    """
    if len(eq.time_slice) == 0:
        return eq

    ts = eq.time_slice[0]

    # --- Complete b_field_r/z/phi only if missing ---
    if len(ts.profiles_2d) > 0 and not ts.profiles_2d[0].b_field_r.has_value:
        print("  [equilibrium] Completing b_field_r, b_field_z, b_field_phi from psi", flush=True)
        try:
            _update_equilibrium_bfield(eq)
        except Exception as e:
            print(f"  [equilibrium] WARNING: Could not compute b_field: {e}", flush=True)

    # --- NaN replacement in 2D profiles ---
    if len(ts.profiles_2d) > 0 and ts.profiles_2d[0].b_field_r.has_value:
        p2d = ts.profiles_2d[0]
        if np.isnan(p2d.b_field_r).any():
            print("  [equilibrium] Replacing NaN in 2D profiles", flush=True)
            p2d.b_field_r[np.isnan(p2d.b_field_r)] = 0.0
            p2d.b_field_z[np.isnan(p2d.b_field_z)] = 0.0
            p2d.b_field_phi[np.isnan(p2d.b_field_phi)] = \
                np.sign(eq.vacuum_toroidal_field.b0) * 99.0
            p2d.psi[np.isnan(p2d.psi)] = ts.global_quantities.psi_boundary

            # Smooth to avoid grid irregularities near separatrix
            if gaussian_filter is not None:
                p2d.b_field_r = gaussian_filter(p2d.b_field_r, sigma=2)
                p2d.b_field_z = gaussian_filter(p2d.b_field_z, sigma=2)
                p2d.b_field_phi = gaussian_filter(p2d.b_field_phi, sigma=2)
                p2d.psi = gaussian_filter(p2d.psi, sigma=2)

    # --- b_field_tor → b_field_phi (DD 3.42 had both) ---
    if hasattr(ts.global_quantities.magnetic_axis, 'b_field_tor'):
        if not ts.global_quantities.magnetic_axis.b_field_phi.has_value \
           and ts.global_quantities.magnetic_axis.b_field_tor.has_value:
            print("  [equilibrium] Copying b_field_tor → b_field_phi (magnetic_axis)", flush=True)
            ts.global_quantities.magnetic_axis.b_field_phi = \
                ts.global_quantities.magnetic_axis.b_field_tor

    if len(ts.profiles_2d) > 0 and hasattr(ts.profiles_2d[0], 'b_field_tor'):
        if not ts.profiles_2d[0].b_field_phi.has_value \
           and ts.profiles_2d[0].b_field_tor.has_value:
            print("  [equilibrium] Copying b_field_tor → b_field_phi (profiles_2d)", flush=True)
            ts.profiles_2d[0].b_field_phi = ts.profiles_2d[0].b_field_tor

    # --- Fill vacuum quantities from magnetic axis if missing ---
    if eq.vacuum_toroidal_field.b0.has_value:
        pass  # already present
    elif ts.global_quantities.magnetic_axis.b_field_phi.has_value:
        print("  [equilibrium] Filling vacuum_toroidal_field from magnetic_axis", flush=True)
        eq.vacuum_toroidal_field.b0.resize(1)
        eq.vacuum_toroidal_field.b0[0] = ts.global_quantities.magnetic_axis.b_field_phi
        eq.vacuum_toroidal_field.r0 = ts.global_quantities.magnetic_axis.r

    # --- triangularity_lower from triangularity_upper if missing ---
    # Required by Cyrano IC wave solver. Shot 134173 is known to have
    # triangularity_upper populated but triangularity_lower empty.
    # Reference: run_cyrano standalone script, confirmed by Mireille.
    if hasattr(ts, 'profiles_1d'):
        if not ts.profiles_1d.triangularity_lower.has_value \
           and ts.profiles_1d.triangularity_upper.has_value:
            print("  [equilibrium] Copying triangularity_upper → triangularity_lower", flush=True)
            ts.profiles_1d.triangularity_lower = \
                copy.deepcopy(ts.profiles_1d.triangularity_upper)

    return eq


def _update_equilibrium_bfield(eq):
    """Compute b_field_r/z/phi from psi for equilibrium profiles_2d.

    Ported from Torbeam's add_bfield.py (UpdateEquilibrium).
    Handles two cases:
      - profiles_2d empty (GGD/NICE case): interpolate from ggd to 2D grid
      - profiles_2d present (DINA case): derive Br/Bz/Bphi from psi and f
    """
    from scipy.interpolate import griddata as scipy_griddata

    N_grid_r = 101
    N_grid_z = 103

    ts = eq.time_slice[0]

    if len(ts.profiles_2d) == 0:
        # GGD case (NICE): interpolate from ggd to rectangular grid
        ts.profiles_2d.resize(1)
        ts.profiles_2d[0].grid_type.index = 1

        phi = np.abs(ts.ggd[0].phi[0].values)
        phi[np.where(phi > 1.e40)] = np.nan
        rr = ts.ggd[0].r[0].values
        zz = ts.ggd[0].z[0].values

        rho = np.full(len(phi), np.nan)
        valid = np.where(~np.isnan(phi))
        try:
            rho[valid] = np.sqrt(phi[valid] / np.max(phi[valid]))
        except Exception:
            print("  [equilibrium] WARNING: equilibrium likely did not converge", flush=True)
            return

        # Use hardcoded ITER-base values for R,Z range
        r_min, r_max = 3.0, 9.0
        z_min, z_max = -6.0, 6.0

        R_2D, Z_2D = np.meshgrid(
            np.linspace(r_min, r_max, N_grid_r),
            np.linspace(z_min, z_max, N_grid_z))

        ts.profiles_2d[0].grid_type.name = 'rectangular'
        ts.profiles_2d[0].grid_type.index = 1
        ts.profiles_2d[0].grid.dim1 = R_2D[0, :]
        ts.profiles_2d[0].grid.dim2 = Z_2D[:, 0]
        ts.profiles_2d[0].r = R_2D.T
        ts.profiles_2d[0].z = Z_2D.T

        for field in ['psi', 'phi', 'b_field_r', 'b_field_phi', 'b_field_z', 'j_phi']:
            try:
                src_vals = getattr(ts.ggd[0], field)[0].values
                setattr(ts.profiles_2d[0], field,
                        scipy_griddata((rr, zz), src_vals, (R_2D, Z_2D)).T)
            except Exception as e:
                print(f"  [equilibrium] WARNING: Could not interpolate {field}: {e}", flush=True)
    else:
        # DINA case: derive Br, Bz, Bphi from psi and f profiles
        _compute_b2d(eq)
        _compute_bax(eq)


def _compute_b2d(eq):
    """Compute 2D magnetic field components from psi (DINA/profiles_2d case).

    Ported from add_bfield.py: UpdateEquilibriumB2d.
    """
    import math

    cocos_psi = 1.0  # 1 for DDV4 (cocos=17), -1 for DDV3 (cocos=11)

    for ts in eq.time_slice:
        if len(ts.profiles_2d) == 0:
            continue

        psi2d = cocos_psi * ts.profiles_2d[0].psi
        psi1d = cocos_psi * ts.profiles_1d.psi
        f1d = ts.profiles_1d.f

        r = ts.profiles_2d[0].grid.dim1
        z = ts.profiles_2d[0].grid.dim2

        nr, nz = len(r), len(z)
        br = np.zeros(psi2d.shape)
        bz = np.zeros(psi2d.shape)
        bt = np.zeros(psi2d.shape)

        dr = r[2] - r[1]
        dz = z[2] - z[1]

        for ir in range(nr):
            for iz in range(nz):
                # Br from -dpsi/dz / (2*pi*R)
                if iz == 0:
                    br[ir, iz] = -(psi2d[ir, iz+1] - psi2d[ir, iz]) / (2.0 * math.pi * r[ir] * dz)
                elif iz == nz - 1:
                    br[ir, iz] = -(psi2d[ir, iz] - psi2d[ir, iz-1]) / (2.0 * math.pi * r[ir] * dz)
                else:
                    br[ir, iz] = -0.5 * (psi2d[ir, iz+1] - psi2d[ir, iz-1]) / (2.0 * math.pi * r[ir] * dz)

                # Bz from dpsi/dr / (2*pi*R)
                if ir == 0:
                    bz[ir, iz] = (psi2d[ir+1, iz] - psi2d[ir, iz]) / (2.0 * math.pi * r[ir] * dr)
                elif ir == nr - 1:
                    bz[ir, iz] = (psi2d[ir, iz] - psi2d[ir-1, iz]) / (2.0 * math.pi * r[ir] * dr)
                else:
                    bz[ir, iz] = 0.5 * (psi2d[ir+1, iz] - psi2d[ir-1, iz]) / (2.0 * math.pi * r[ir] * dr)

                # Bt = F(psi) / R
                bt[ir, iz] = np.interp(psi2d[ir, iz], psi1d, f1d) / r[ir]

        ts.profiles_2d[0].b_field_r = br
        ts.profiles_2d[0].b_field_z = bz
        ts.profiles_2d[0].b_field_phi = bt


def _compute_bax(eq):
    """Compute magnetic axis b_field_phi.

    Ported from add_bfield.py: UpdateEquilibriumBax.
    """
    for ts in eq.time_slice:
        rmag = ts.global_quantities.magnetic_axis.r
        if not (rmag > 0.):
            rmag = eq.vacuum_toroidal_field.r0

        psi1d = ts.profiles_1d.psi
        psi_ax = ts.global_quantities.psi_axis
        if abs(psi1d[0] - psi_ax) < abs(psi1d[-1] - psi_ax):
            f_ax = ts.profiles_1d.f[0]
        else:
            f_ax = ts.profiles_1d.f[-1]

        if abs(f_ax) > 0.:
            b_field_ax = f_ax / rmag
        else:
            b_field_ax = eq.vacuum_toroidal_field.b0[0] * eq.vacuum_toroidal_field.r0 / rmag

        ts.global_quantities.magnetic_axis.b_field_phi = b_field_ax


def safe_get_ids(db_entry, ids_name):
    """Safely get an IDS from database, with smart DD conversion."""
    try:
        ids_object = db_entry.get(ids_name, autoconvert=False)
        ids_object = _smart_convert(ids_object, ids_name)
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

# forget about non-imas-python
def _create_ids(ids_name: str):
    """Create an empty IDS object by name."""
    if hasattr(imas, 'IDSFactory'):
        factory = imas.IDSFactory()
        return getattr(factory, ids_name)()
    elif hasattr(imas, ids_name):
        return getattr(imas, ids_name)()
    else:
        raise AttributeError(f"Cannot create IDS '{ids_name}': not found in imas module")


def _safe_partial_get(db_entry, ids_name: str, data_path: str, occurrence: int = 0):
    """Safely get a partial IDS field from a database entry."""
    try:
        if hasattr(db_entry, 'partial_get'):
            return db_entry.partial_get(ids_name=ids_name, data_path=data_path, occurrence=occurrence)
        else:
            try:
                ids_object = db_entry.get(ids_name, occurrence, autoconvert=False)
                ids_object = _smart_convert(ids_object, ids_name)
                result = ids_object
                for part in data_path.split('/'):
                    if part:
                        result = getattr(result, part)
                return result
            except Exception as e:
                if 'empty' in str(e).lower():
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
    'equilibrium_out',
    'core_profiles_out',
    'workflow_out',
    'ec_launchers_out',
    'ic_antennas_out',
    'core_sources_out',
    'distributions_out',
    'distribution_sources_out',
]

# Ports that receive IDS from micro to macro (O_F → S)
RECV_PORTS = [
    'core_sources_in',
    'waves_in',
    'core_profiles_in',
    'distributions_in',
]


def _port_to_ids(port_name):
    """Convert port name to IDS name: 'equilibrium_out' → 'equilibrium'."""
    return port_name.rsplit('_', 1)[0]


# =============================================================================
# Database Setup (shared by both modes)
# =============================================================================

def setup_databases(config_folder_path):
    """
    Initialize all databases and load machine descriptions.
    Returns: (inputDb, outputDb, machineDb, inputIds, inputMds, wf_parameters)
    """
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

    dbhelper = WorkflowDbHelper(
        input_user_or_path, input_database, input_backend, ddv_backend,
        output_user_or_path, output_database, output_backend,
        shot_nr, run_in, run_out,
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

    return inputDb, outputDb, machineDb, inputIds, inputMds, wf_parameters


# =============================================================================
# Database I/O Helpers
# =============================================================================

def get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow):
    """Read all IDS slices at the given time, with smart DD conversion."""
    slices = {}
    for ids_name in inputIds:
        try:
            ids_obj = inputDb.get_slice(ids_name, timenow, 1, autoconvert=False)
            slices[ids_name] = _smart_convert(ids_obj, ids_name)
        except Exception as e:
            if 'empty' in str(e).lower():
                slices[ids_name] = _create_ids(ids_name)
            else:
                print(f"  ERROR reading {ids_name} at t={timenow}: {e}", flush=True)
                return None
    for ids_name in inputMds:
        try:
            ids_obj = machineDb.get_slice(ids_name, timenow, 1, autoconvert=False)
            slices[ids_name] = _smart_convert(ids_obj, ids_name)
        except Exception:
            pass
    return slices


def store_ids_slices(outputDb, inputMds, input_slices, output_ids, m3_flag=0):
    """Write IDS slices to the output database."""
    for ids_name, ids_data in input_slices.items():
        if ids_name in inputMds:
            continue
        if hasattr(ids_data, 'ids_properties') and ids_data.ids_properties.homogeneous_time >= 0:
            outputDb.put_slice(ids_data)

    for ids_name, ids_data in output_ids.items():
        if hasattr(ids_data, 'time') and len(ids_data.time) > 0:
            if ids_name != "equilibrium" and ids_data.time[0] > 0:
                if m3_flag == 1:
                    # Re-serialize to avoid C-level segfaults with deserialized objects
                    clean_ids = _create_ids(ids_name)
                    clean_ids.deserialize(ids_data.serialize())
                    outputDb.put_slice(clean_ids)
                else:
                    outputDb.put_slice(ids_data)


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
            if tbegin < 0: tbegin = time_array[0]
            if tend < 0:   tend = time_array[-1]
    else:
        tend = tbegin + dt

    nsteps = 1 if one_time_slice else int((tend - tbegin) / dt)
    if dt * nsteps < (tend - tbegin):
        nsteps += 1

    return tbegin, tend, dt, nsteps, one_time_slice


# =============================================================================
# Mode 0: Traditional iwrap
# =============================================================================

def run_traditional(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds):
    """
    Run in traditional mode: time loop + HCDWorkflow.run() directly.
    No MUSCLE3 involvement. All iWrap actors execute in-process.
    """
    print("[wf_wrapper] Initializing HCDWorkflow (traditional mode)...", flush=True)

    workflow = HCDWorkflow()
    workflow.initialize(config_folder_path)

    tbegin, tend, dt, nsteps, one_time_slice = resolve_time_range(workflow, inputDb)
    print(f"[wf_wrapper] Time range: {tbegin} → {tend}, dt={dt}, steps={nsteps}", flush=True)

    # --- Time loop ---
    timenow = tbegin
    step = 0

    while timenow < tend:
        step += 1
        print(f"---------------------------------------------", flush=True)
        print(f"[wf_wrapper] Step {step}/{nsteps}, t={timenow:.4f}, dt={dt:.4f}", flush=True)

        # Read IDS from database
        ids_slices = get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow)
        if ids_slices is None:
            print(f"[wf_wrapper] ERROR: Failed to read IDS at t={timenow}", flush=True)
            timenow += dt
            continue

        # Separate mandatory and optional IDS
        nonmandatory = {k: v for k, v in ids_slices.items()
                        if k not in ("equilibrium", "core_profiles", "workflow")}

        # Set process status and run
        workflow.setProcessStatus(timenow)
        workflow.run(
            equilibrium=ids_slices["equilibrium"],
            core_profiles=ids_slices["core_profiles"],
            workflow=ids_slices["workflow"],
            **nonmandatory,
        )

        # Store results
        output_ids = workflow._getIDSes()
        store_ids_slices(outputDb, inputMds, ids_slices, output_ids, m3_flag=0)

        timenow += dt

    print(f"[wf_wrapper] Finished after {step} steps", flush=True)


# =============================================================================
# Mode 1: MUSCLE3 Hybrid (Macro Model)
# =============================================================================

def run_m3_macro(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds):
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
        Operator.S:   RECV_PORTS,
    }
    instance = Instance(ports, InstanceFlags.SKIP_MMSF_SEQUENCE_CHECKS)

    print(f"[wf_wrapper] M3 macro instance created", flush=True)
    print(f"  O_I (send → micro): {SEND_PORTS}", flush=True)
    print(f"  S   (recv ← micro): {RECV_PORTS}", flush=True)

    # --- Resolve time range ---
    wf_config = HCDWorkflow()
    wf_config.initialize(config_folder_path)
    tbegin, tend, dt, nsteps, one_time_slice = resolve_time_range(wf_config, inputDb)
    print(f"[wf_wrapper] Time range: {tbegin} → {tend}, dt={dt}, steps={nsteps}", flush=True)

    # --- Determine connected ports ---
    connected_send = [p for p in SEND_PORTS if instance.is_connected(p)]
    connected_recv = [p for p in RECV_PORTS if instance.is_connected(p)]
    print(f"[wf_wrapper] Connected send ports: {connected_send}", flush=True)
    print(f"[wf_wrapper] Connected recv ports: {connected_recv}", flush=True)

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

            print(f"---------------------------------------------", flush=True)
            print(f"[wf_wrapper] Step {step}/{nsteps}, t={timenow:.4f}, dt={dt:.4f}", flush=True)

            # --- Read IDS from database ---
            ids_slices = get_ids_slices(inputDb, machineDb, inputIds, inputMds, timenow)
            if ids_slices is None:
                print(f"[wf_wrapper] ERROR: Failed to read IDS at t={timenow}", flush=True)
                timenow += dt
                continue

            # --- O_I: Send IDS to hcd_workflow ---
            for port_name in connected_send:
                ids_name = _port_to_ids(port_name)
                ids_data = ids_slices.get(ids_name)

                # Safely serialize: some IDS may be empty (homogeneous_time undefined)
                serialized = None
                if ids_data is not None:
                    try:
                        serialized = ids_data.serialize()
                    except (ValueError, RuntimeError) as e:
                        print(f"  -> {ids_name} cannot be serialized ({e}), sending empty", flush=True)

                if serialized is None:
                    # Create a minimal valid IDS that can be serialized.
                    # Use homogeneous_time=0 (not 1) so that workflow_executor's
                    # fix-up logic (homogeneous_time < 1 check) still detects these
                    # as empty and repairs them (e.g., copies time from core_profiles).
                    empty_ids = _create_ids(ids_name)
                    empty_ids.ids_properties.homogeneous_time = 0
                    try:
                        serialized = empty_ids.serialize()
                    except (ValueError, RuntimeError):
                        serialized = b''  # absolute fallback

                print(f"  -> Sending {ids_name} on {port_name} ({len(serialized)} bytes)", flush=True)
                instance.send(port_name, Message(timenow, t_next, data=serialized))

            # --- S: Receive updated IDS from hcd_workflow ---
            output_ids = {}
            for port_name in connected_recv:
                ids_name = _port_to_ids(port_name)
                print(f"  <- Waiting for {ids_name} on {port_name}...", flush=True)
                msg = instance.receive(port_name)

                ids_obj = _create_ids(ids_name)
                if msg.data and len(msg.data) > 0:
                    try:
                        ids_obj.deserialize(msg.data)
                        if ids_obj.ids_properties.homogeneous_time == -1:
                            print(f"  <- {ids_name}: marked invalid (not produced this timestep)", flush=True)
                        else:
                            # Stamp authoritative global time before writing to DB
                            if hasattr(ids_obj, 'time'):
                                ids_obj.time = np.array([timenow])
                    except Exception as e:
                        print(f"  <- WARNING: Could not deserialize {ids_name}: {e}", flush=True)

                output_ids[ids_name] = ids_obj
                print(f"  <- Received {ids_name} (t={msg.timestamp:.4f})", flush=True)

            # --- Store results to database ---
            store_ids_slices(outputDb, inputMds, ids_slices, output_ids, m3_flag=1)

            timenow += dt

    print(f"[wf_wrapper] Finished after {step} steps", flush=True)


# =============================================================================
# Entry Point
# =============================================================================

def wf_wrapper(par_path, m3_flag=0):
    """
    Main workflow wrapper function.

    Args:
        par_path: Path to the configuration folder containing input_workflow.xml
        m3_flag: Execution mode
            - 0: Traditional mode (HCDWorkflow.run() in-process)
            - 1: MUSCLE3 macro (sends IDS to hcd_workflow micro via M3)
    """
    print("=" * 60, flush=True)
    print(f"[wf_wrapper] Starting HCD Workflow", flush=True)
    print(f"[wf_wrapper] Mode: {'MUSCLE3 Macro' if m3_flag == 1 else 'Traditional iwrap'}", flush=True)
    print(f"[wf_wrapper] Config path: {par_path}", flush=True)
    print("=" * 60, flush=True)

    config_folder_path = os.path.abspath(par_path)

    # Database setup is the same for both modes
    inputDb, outputDb, machineDb, inputIds, inputMds, wf_parameters = \
        setup_databases(config_folder_path)

    # Dispatch based on mode
    if m3_flag == 1:
        run_m3_macro(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds)
    else:
        run_traditional(config_folder_path, inputDb, outputDb, machineDb, inputIds, inputMds)

    # Cleanup
    print("[wf_wrapper] Closing databases...")
    inputDb.close()
    outputDb.close()
    machineDb.close()

    print("=" * 60)
    print("[wf_wrapper] Workflow completed successfully")
    print("=" * 60)


def wf_wrapper_m3(par_path):
    """Convenience function to run workflow in MUSCLE3 hybrid mode."""
    return wf_wrapper(par_path, m3_flag=1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wf_wrapper_m3.py <config_path> [m3_flag]")
        print("  config_path: Path to configuration folder")
        print("  m3_flag: 0=traditional iwrap, 1=MUSCLE3 macro (default: 0)")
        sys.exit(1)

    config_path = sys.argv[1]
    m3_flag = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    wf_wrapper(config_path, m3_flag=m3_flag)