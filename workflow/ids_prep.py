"""
ids_prep.py — IDS Data Preparation Helpers

This module groups two related concerns:

1. **DD Conversion & Fixup** — applied when reading IDSes from input.
   `_smart_convert` runs `imas.convert_ids` if the source DD differs from the
   target, then patches fields that don't survive conversion or are missing
   in the source data (b_field components, triangularity, ion fields, etc).

2. **Output Placeholders & Stabilization** — applied before writing IDSes.
   Ensures `core_sources` and `waves` always have the expected source/wave
   slots (EC, IC) and that all per-source `global_quantities` fields are
   present. This avoids HDF5 schema growth across timesteps where some
   fields are only written by certain codes (e.g. CYRANO writes
   `total_ion_power` only while IC is on).

Both blocks are pure IDS-content transformations and have no dependency on
database connections or workflow drivers.
"""

import copy
import os

import imas
import numpy as np

try:
    from scipy.ndimage import gaussian_filter
except ImportError:
    gaussian_filter = None


# =============================================================================
# IMAS API Compatibility
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
# DD Conversion & Fixup (applied when reading input IDSes)
# =============================================================================

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
    elif ids_name == 'core_profiles':
        ids_object = _fixup_core_profiles(ids_object)

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


def _repair_axis_minor_radius(ts, r_outboard, r_inboard):
    """Keep the first off-axis midplane point from collapsing onto the axis."""
    r_outboard = np.asarray(r_outboard, dtype=float).copy()
    r_inboard = np.asarray(r_inboard, dtype=float).copy()

    if len(r_outboard) < 3 or len(r_inboard) < 3:
        return r_outboard, r_inboard, False

    rho = 0.5 * (r_outboard - r_inboard)
    eps = max(1e-9, abs(float(rho[2])) * 1e-6)
    if not np.isfinite(rho[1]) or rho[1] > rho[0] + eps:
        return r_outboard, r_inboard, False

    rho1 = np.nan
    if ts.profiles_1d.rho_tor_norm.has_value and len(ts.profiles_1d.rho_tor_norm) > 2:
        rho_norm = np.asarray(ts.profiles_1d.rho_tor_norm, dtype=float)
        if np.isfinite(rho_norm[1]) and np.isfinite(rho_norm[2]) and rho_norm[2] > 0:
            rho1 = rho[2] * rho_norm[1] / rho_norm[2]

    if not np.isfinite(rho1) or rho1 <= rho[0] + eps:
        rho1 = 0.5 * rho[2]

    r_mid = 0.5 * (r_outboard[1] + r_inboard[1])
    if not np.isfinite(r_mid):
        r_mid = float(ts.global_quantities.magnetic_axis.r)

    r_outboard[1] = r_mid + rho1
    r_inboard[1] = r_mid - rho1
    return r_outboard, r_inboard, True


def _fixup_core_profiles(cp):
    """Fill ion fields that are empty after legacy DD conversion."""
    if len(cp.profiles_1d) == 0:
        return cp

    cp1 = cp.profiles_1d[0]
    t_i_avg = np.asarray(cp1.t_i_average)
    if t_i_avg.size == 0:
        return cp

    n_fixed_temp = 0
    n_fixed_density = 0
    n_fixed_flag = 0

    for ion in cp1.ion:
        if len(np.asarray(ion.temperature)) == 0:
            ion.temperature = t_i_avg.copy()
            n_fixed_temp += 1

        if len(np.asarray(ion.density_thermal)) == 0:
            density = np.asarray(ion.density)
            if density.size > 0:
                ion.density_thermal = density.copy()
                n_fixed_density += 1

        try:
            multiple_states_flag = int(ion.multiple_states_flag)
        except Exception:
            multiple_states_flag = get_empty_int()
        if multiple_states_flag < 0 or multiple_states_flag > 10:
            ion.multiple_states_flag = 0
            n_fixed_flag += 1

    if n_fixed_temp or n_fixed_density or n_fixed_flag:
        print(f"  [core_profiles] Filled ion fields for Cyrano "
              f"(temperature={n_fixed_temp}, density_thermal={n_fixed_density}, "
              f"multiple_states_flag={n_fixed_flag})", flush=True)

    return cp


def _eq_fill_psi_axis(ts):
    """Fill psi_axis from profiles_1d.psi[0] when missing (CHEASE/DINA workaround).

    Some scenarios (e.g. ITER 105102) leave global_quantities.psi_axis as the
    IMAS empty sentinel (-9e+40). Downstream code (including _compute_bax and
    Cyrano's axis-side f-profile picker) compares it against profiles_1d.psi
    to decide which end is the axis; with the sentinel the comparison is
    numerical noise. profiles_1d.psi is ordered axis→boundary, so psi_axis
    = psi1d[0] is the correct recovery.
    """
    if ts.global_quantities.psi_axis.has_value or len(ts.profiles_1d.psi) == 0:
        return
    psi1d_axis = float(np.asarray(ts.profiles_1d.psi)[0])
    ts.global_quantities.psi_axis = psi1d_axis
    print(f"  [equilibrium] Filled psi_axis from profiles_1d.psi[0] "
          f"(= {psi1d_axis:.4g})", flush=True)


def _eq_complete_bfield(eq, ts):
    """Compute b_field_r/z/phi from psi when missing."""
    if len(ts.profiles_2d) == 0 or ts.profiles_2d[0].b_field_r.has_value:
        return
    print("  [equilibrium] Completing b_field_r, b_field_z, b_field_phi from psi", flush=True)
    try:
        _update_equilibrium_bfield(eq)
    except Exception as e:
        print(f"  [equilibrium] WARNING: Could not compute b_field: {e}", flush=True)


def _eq_replace_nan_2d(eq, ts):
    """Replace NaN in 2D profiles and lightly smooth to tame separatrix grid."""
    if len(ts.profiles_2d) == 0 or not ts.profiles_2d[0].b_field_r.has_value:
        return
    p2d = ts.profiles_2d[0]
    if not np.isnan(p2d.b_field_r).any():
        return
    print("  [equilibrium] Replacing NaN in 2D profiles", flush=True)
    p2d.b_field_r[np.isnan(p2d.b_field_r)] = 0.0
    p2d.b_field_z[np.isnan(p2d.b_field_z)] = 0.0
    p2d.b_field_phi[np.isnan(p2d.b_field_phi)] = \
        np.sign(float(eq.vacuum_toroidal_field.b0[0])) * 99.0
    p2d.psi[np.isnan(p2d.psi)] = ts.global_quantities.psi_boundary

    if gaussian_filter is not None:
        p2d.b_field_r = gaussian_filter(p2d.b_field_r, sigma=2)
        p2d.b_field_z = gaussian_filter(p2d.b_field_z, sigma=2)
        p2d.b_field_phi = gaussian_filter(p2d.b_field_phi, sigma=2)
        p2d.psi = gaussian_filter(p2d.psi, sigma=2)


def _eq_rename_b_field_tor(ts):
    """DD 3.42 had b_field_tor; copy into b_field_phi when only the legacy
    field is populated."""
    mag = ts.global_quantities.magnetic_axis
    if hasattr(mag, 'b_field_tor') \
       and not mag.b_field_phi.has_value \
       and mag.b_field_tor.has_value:
        print("  [equilibrium] Copying b_field_tor → b_field_phi (magnetic_axis)", flush=True)
        mag.b_field_phi = mag.b_field_tor

    if len(ts.profiles_2d) > 0 and hasattr(ts.profiles_2d[0], 'b_field_tor') \
       and not ts.profiles_2d[0].b_field_phi.has_value \
       and ts.profiles_2d[0].b_field_tor.has_value:
        print("  [equilibrium] Copying b_field_tor → b_field_phi (profiles_2d)", flush=True)
        ts.profiles_2d[0].b_field_phi = ts.profiles_2d[0].b_field_tor


def _eq_fill_vacuum_field(eq, ts):
    """Fill vacuum_toroidal_field from magnetic_axis when missing."""
    if eq.vacuum_toroidal_field.b0.has_value:
        return
    if not ts.global_quantities.magnetic_axis.b_field_phi.has_value:
        return
    print("  [equilibrium] Filling vacuum_toroidal_field from magnetic_axis", flush=True)
    eq.vacuum_toroidal_field.b0.resize(1)
    eq.vacuum_toroidal_field.b0[0] = ts.global_quantities.magnetic_axis.b_field_phi
    eq.vacuum_toroidal_field.r0 = ts.global_quantities.magnetic_axis.r


def _eq_complete_triangularity(ts):
    """Fill triangularity / elongation profiles for Cyrano.

    Two-step recovery:
      1. triangularity_lower from triangularity_upper if upper is populated
         (takes priority);
      2. otherwise, if both triangularity profiles and elongation are empty
         but a boundary outline exists, derive linear axis-to-edge profiles
         from the outline geometry.
    """
    if not hasattr(ts, 'profiles_1d'):
        return

    if not ts.profiles_1d.triangularity_lower.has_value \
       and ts.profiles_1d.triangularity_upper.has_value:
        print("  [equilibrium] Copying triangularity_upper → triangularity_lower", flush=True)
        ts.profiles_1d.triangularity_lower = \
            copy.deepcopy(ts.profiles_1d.triangularity_upper)
        return  # priority: don't also derive from outline

    if not (
        len(ts.profiles_1d.psi) > 0
        and len(ts.profiles_1d.elongation) == 0
        and not ts.profiles_1d.triangularity_lower.has_value
        and len(ts.boundary.outline.r) > 0
    ):
        return

    try:
        r_bnd = np.array(ts.boundary.outline.r)
        z_bnd = np.array(ts.boundary.outline.z)
        nrho = len(ts.profiles_1d.psi)

        a_minor = (r_bnd.max() - r_bnd.min()) / 2.0
        R0 = (r_bnd.max() + r_bnd.min()) / 2.0
        kappa_edge = (z_bnd.max() - z_bnd.min()) / (2.0 * a_minor)
        delta_upper_edge = (R0 - r_bnd[np.argmax(z_bnd)]) / a_minor
        delta_lower_edge = (R0 - r_bnd[np.argmin(z_bnd)]) / a_minor

        rho_norm = np.linspace(0, 1, nrho)
        ts.profiles_1d.elongation = 1.0 + (kappa_edge - 1.0) * rho_norm
        ts.profiles_1d.triangularity_upper = delta_upper_edge * rho_norm
        ts.profiles_1d.triangularity_lower = delta_lower_edge * rho_norm

        if float(ts.boundary.triangularity_upper) < -1e30:
            ts.boundary.triangularity_upper = delta_upper_edge
        if float(ts.boundary.triangularity_lower) < -1e30:
            ts.boundary.triangularity_lower = delta_lower_edge

        print(f"  [equilibrium] Computed elongation/triangularity profiles "
              f"(kappa={kappa_edge:.3f}, delta_u={delta_upper_edge:.3f}, "
              f"delta_l={delta_lower_edge:.3f})", flush=True)
    except Exception as e:
        print(f"  [equilibrium] WARNING: Could not compute elongation/triangularity: {e}", flush=True)


def _eq_compute_r_outboard_inboard(ts):
    """Compute r_outboard / r_inboard from 2D psi for Cyrano (CHEASE workaround)."""
    if not (
        hasattr(ts, 'profiles_1d')
        and len(ts.profiles_1d.psi) > 0
        and len(ts.profiles_1d.r_outboard) == 0
        and len(ts.profiles_2d) > 0
        and ts.profiles_2d[0].psi.has_value
        and float(ts.global_quantities.magnetic_axis.r) > 0
    ):
        return

    try:
        from scipy.interpolate import interp1d

        R2d = np.array(ts.profiles_2d[0].r)
        Z2d = np.array(ts.profiles_2d[0].z)
        psi2d = np.array(ts.profiles_2d[0].psi)
        psi1d = np.array(ts.profiles_1d.psi)

        R1d = R2d[:, 0]   # R varies along axis 0
        Z1d = Z2d[0, :]   # Z varies along axis 1

        r_axis = float(ts.global_quantities.magnetic_axis.r)
        z_axis = float(ts.global_quantities.magnetic_axis.z)

        iz_mid = np.argmin(np.abs(Z1d - z_axis))
        psi_mid = psi2d[:, iz_mid]

        ir_axis = np.argmin(np.abs(R1d - r_axis))
        f_out = interp1d(psi_mid[ir_axis:], R1d[ir_axis:],
                         bounds_error=False, fill_value=np.nan)
        f_in = interp1d(psi_mid[:ir_axis + 1], R1d[:ir_axis + 1],
                        bounds_error=False, fill_value=np.nan)

        r_outboard = f_out(psi1d)
        r_inboard = f_in(psi1d)
        r_outboard[np.isnan(r_outboard)] = r_axis
        r_inboard[np.isnan(r_inboard)] = r_axis

        r_outboard, r_inboard, repaired_axis = \
            _repair_axis_minor_radius(ts, r_outboard, r_inboard)

        ts.profiles_1d.r_outboard = r_outboard
        ts.profiles_1d.r_inboard = r_inboard

        print(f"  [equilibrium] Computed r_outboard/r_inboard from 2D psi "
              f"({len(psi1d)} points, R_axis={r_axis:.3f})", flush=True)
        if repaired_axis:
            rho1 = 0.5 * (r_outboard[1] - r_inboard[1])
            print(f"  [equilibrium] Repaired first off-axis minor radius "
                  f"for Cyrano (rho[1]={rho1:.4g} m)", flush=True)
    except Exception as e:
        print(f"  [equilibrium] WARNING: Could not compute r_outboard/r_inboard: {e}", flush=True)


def _fixup_equilibrium(eq):
    """Apply manual fix-ups for equilibrium IDS.

    Runs UNCONDITIONALLY (not only after DD conversion) because these issues
    exist in the source data regardless of DD version. Each helper is
    independently triggerable and prints its own diagnostic; ordering matters
    only where one helper depends on a previous one (e.g. b_field renaming
    must run before vacuum-field fill, which then enables r_outboard from psi).

    Reference: Torbeam standalone run_torbeam, Cyrano standalone run_cyrano.
    """
    if len(eq.time_slice) == 0:
        return eq

    ts = eq.time_slice[0]

    _eq_fill_psi_axis(ts)
    _eq_complete_bfield(eq, ts)
    _eq_replace_nan_2d(eq, ts)
    _eq_rename_b_field_tor(ts)
    _eq_fill_vacuum_field(eq, ts)
    _eq_complete_triangularity(ts)
    _eq_compute_r_outboard_inboard(ts)

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
    Vectorized with np.gradient (matches original edge scheme: forward/backward
    at boundaries, central in interior).
    """
    cocos_psi = 1.0  # 1 for DDV4 (cocos=17), -1 for DDV3 (cocos=11)
    two_pi = 2.0 * np.pi

    for ts in eq.time_slice:
        if len(ts.profiles_2d) == 0:
            continue

        psi2d = cocos_psi * np.asarray(ts.profiles_2d[0].psi)
        psi1d = cocos_psi * np.asarray(ts.profiles_1d.psi)
        f1d = np.asarray(ts.profiles_1d.f)

        r = np.asarray(ts.profiles_2d[0].grid.dim1)
        z = np.asarray(ts.profiles_2d[0].grid.dim2)

        dr = r[2] - r[1]
        dz = z[2] - z[1]
        r_col = r[:, None]  # broadcast along R axis (axis=0)

        dpsi_dr = np.gradient(psi2d, dr, axis=0)
        dpsi_dz = np.gradient(psi2d, dz, axis=1)

        br = -dpsi_dz / (two_pi * r_col)
        bz = dpsi_dr / (two_pi * r_col)

        # Bt = F(psi) / R — np.interp needs monotonic xp; flip if descending
        if psi1d[0] > psi1d[-1]:
            f_at_psi = np.interp(psi2d.ravel(), psi1d[::-1], f1d[::-1])
        else:
            f_at_psi = np.interp(psi2d.ravel(), psi1d, f1d)
        bt = f_at_psi.reshape(psi2d.shape) / r_col

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


# =============================================================================
# Output Placeholders & Stabilization (applied before writing output IDSes)
# =============================================================================

def _process_is_selected(param_process, process_name):
    if not param_process:
        return False
    try:
        return int(param_process.get(process_name, 0)) != 0
    except (TypeError, ValueError):
        return False


def _ids_needs_placeholder(ids_data):
    if ids_data is None:
        return True
    if not hasattr(ids_data, 'ids_properties'):
        return False
    try:
        return int(ids_data.ids_properties.homogeneous_time) < 0
    except (TypeError, ValueError):
        return False


def _ensure_output_slice(output_ids, ids_name, timenow):
    ids_data = output_ids.get(ids_name)
    if _ids_needs_placeholder(ids_data):
        ids_data = _create_ids(ids_name)
        output_ids[ids_name] = ids_data

    ids_data.ids_properties.homogeneous_time = 1
    if hasattr(ids_data, 'time'):
        ids_data.time = np.array([timenow])
    return ids_data


def _safe_len(value):
    try:
        return len(value)
    except Exception:
        return 0


def _set_code(code_obj, name=None, index=None):
    try:
        if name is not None and hasattr(code_obj, 'name'):
            code_obj.name = name
        if index is not None and hasattr(code_obj, 'index'):
            code_obj.index = index
    except Exception:
        pass


def _ec_beam_name(ec_launchers, beam_index):
    try:
        name = str(ec_launchers.beam[beam_index].name)
        if name:
            return name
    except Exception:
        pass
    return f"EC beam {beam_index + 1}"


def _ic_antenna_name(ic_antennas, antenna_index):
    try:
        name = str(ic_antennas.antenna[antenna_index].name)
        if name:
            return name
    except Exception:
        pass
    return "Unknown"


def _first_numeric(value, default=0.0):
    try:
        if hasattr(value, 'data') and len(value.data) > 0:
            return float(np.asarray(value.data).flat[0])
        arr = np.asarray(value)
        if arr.size > 0:
            return float(arr.flat[0])
    except Exception:
        pass
    return default


def _ic_frequency(input_slices, antenna_index):
    try:
        antenna = input_slices.get("ic_antennas").antenna[antenna_index]
        return _first_numeric(antenna.frequency, 0.0)
    except Exception:
        return 0.0


def _xml_int(config_folder_path, relative_path, tag_name, default=None):
    if not config_folder_path:
        return default
    try:
        from hcdworkflow.workflow_config_reader import XmlReader
        reader = XmlReader(os.path.join(config_folder_path, relative_path))
        elem = reader.xmlRoot.find(f".//{tag_name}")
        if elem is not None and elem.text is not None:
            return int(float(elem.text.strip()))
    except Exception:
        pass
    return default


def _wave_array_shape(coherent_wave, path):
    try:
        value = coherent_wave
        for part in path:
            value = value[part] if isinstance(part, int) else getattr(value, part)
        if getattr(value, 'has_value', False):
            shape = np.asarray(value).shape
            if shape and all(dim > 0 for dim in shape):
                return shape
    except Exception:
        pass
    return None


def _first_wave_array_shape(waves, path):
    try:
        for coherent_wave in waves.coherent_wave:
            shape = _wave_array_shape(coherent_wave, path)
            if shape:
                return shape
    except Exception:
        pass
    return None


def _radial_size(input_slices, waves=None):
    for path in (
        ("profiles_1d", 0, "power_density"),
        ("profiles_1d", 0, "grid", "rho_tor_norm"),
    ):
        shape = _first_wave_array_shape(waves, path)
        if shape:
            return int(shape[0])

    for ids_name, path in (
        ("core_profiles", ("profiles_1d", 0, "grid", "rho_tor_norm")),
        ("core_profiles", ("profiles_1d", 0, "rho_tor_norm")),
        ("equilibrium", ("time_slice", 0, "profiles_1d", "rho_tor_norm")),
    ):
        try:
            value = input_slices.get(ids_name)
            for part in path:
                value = value[part] if isinstance(part, int) else getattr(value, part)
            size = len(value)
            if size > 0:
                return size
        except Exception:
            pass
    return 0


def _n_phi_values(waves=None, config_folder_path=None):
    for path in (
        ("global_quantities", 0, "n_phi"),
        ("profiles_1d", 0, "n_phi"),
        ("profiles_2d", 0, "n_phi"),
    ):
        shape = _first_wave_array_shape(waves, path)
        if shape:
            return np.zeros(shape[0], dtype=np.int32)

    ntor = _xml_int(config_folder_path, "ICRH/ic_wave_solver/input_cyrano.xml", "Ntor", 0)
    if ntor and ntor > 0:
        return np.array([ntor], dtype=np.int32)
    return np.zeros(1, dtype=np.int32)


def _n_phi_values_for_wave(coherent_wave):
    for path in (
        ("global_quantities", 0, "n_phi"),
        ("profiles_1d", 0, "n_phi"),
        ("profiles_2d", 0, "n_phi"),
    ):
        shape = _wave_array_shape(coherent_wave, path)
        if shape:
            return np.zeros(shape[0], dtype=np.int32)
    return None


def _poloidal_size(waves=None, config_folder_path=None):
    for path in (
        ("profiles_2d", 0, "power_density"),
        ("profiles_2d", 0, "grid", "r"),
        ("profiles_2d", 0, "e_field_n_phi", 0, "plus", "amplitude"),
    ):
        shape = _first_wave_array_shape(waves, path)
        if shape and len(shape) >= 2:
            return int(shape[1])

    npol = _xml_int(config_folder_path, "ICRH/ic_wave_solver/input_cyrano.xml", "Npol", None)
    if npol is None:
        return 0
    return (2 ** max(npol - 3, 0)) + 1


def _poloidal_size_for_wave(coherent_wave):
    for path in (
        ("profiles_2d", 0, "power_density"),
        ("profiles_2d", 0, "grid", "r"),
        ("profiles_2d", 0, "e_field_n_phi", 0, "plus", "amplitude"),
    ):
        shape = _wave_array_shape(coherent_wave, path)
        if shape and len(shape) >= 2:
            return int(shape[1])
    return 0


def _ion_count(input_slices):
    try:
        return len(input_slices["core_profiles"].profiles_1d[0].ion)
    except Exception:
        return 0


def _ion_metadata(input_slices, ion_index):
    name = f"ion{ion_index + 1}"
    z_ion = float(ion_index + 1)
    a = float(2 * (ion_index + 1))
    z_n = ion_index + 1
    try:
        ion = input_slices["core_profiles"].profiles_1d[0].ion[ion_index]
        for attr in ("label", "name"):
            if hasattr(ion, attr):
                candidate = str(getattr(ion, attr))
                if candidate:
                    name = candidate
                    break
        if hasattr(ion, "z_ion") and ion.z_ion.has_value:
            z_ion = float(ion.z_ion)
        if len(ion.element) > 0:
            if ion.element[0].a.has_value:
                a = float(ion.element[0].a)
            if ion.element[0].z_n.has_value:
                z_n = int(ion.element[0].z_n)
    except Exception:
        pass
    return name, z_ion, a, z_n


def _has_imas_value(value):
    try:
        return bool(value.has_value)
    except Exception:
        return False


def _set_if_missing(obj, field_name, value):
    """Assign `value` to `obj.field_name` only when the field is unset.

    Use this for output stabilization where actor-written values must be
    preserved. For unconditional zeroing of stale values, use
    `_zero_field_like` instead.
    """
    try:
        if not _has_imas_value(getattr(obj, field_name)):
            setattr(obj, field_name, value)
    except Exception:
        pass


def _set_zero_if_missing(obj, field_name):
    """Assign scalar 0.0 to `obj.field_name` if the field is unset."""
    _set_if_missing(obj, field_name, 0.0)


def _force_zero_if_negative_int(obj, field_name):
    """Force-zero an int field if it reads as negative (IMAS sentinel) or
    raises during int() coercion. Used for flag/index fields where the IDS
    default is the EMPTY_INT sentinel rather than has_value=False."""
    try:
        if int(getattr(obj, field_name)) >= 0:
            return
    except Exception:
        pass
    try:
        setattr(obj, field_name, 0)
    except Exception:
        pass


def _fill_ion_metadata(ion_obj, name, z_ion, a, z_n, flavor):
    """Fill ion metadata for either wave (`flavor="wave"`) or core_sources
    (`flavor="source"`).

    Both flavors use has_value/sentinel guards so a non-empty ion is never
    clobbered. Wave-specific fields (`name`, `distribution_assumption`) are
    set only for `flavor="wave"`; core_sources-specific fields
    (`neutral_index`, `element[0].atoms_n`) only for `flavor="source"`.
    """
    if flavor == "wave":
        _set_if_missing(ion_obj, "name", name)
        _set_if_missing(ion_obj, "distribution_assumption", 0)

    _set_if_missing(ion_obj, "z_ion", z_ion)
    _force_zero_if_negative_int(ion_obj, "multiple_states_flag")

    if flavor == "source":
        _force_zero_if_negative_int(ion_obj, "neutral_index")

    try:
        if _safe_len(ion_obj.element) == 0:
            ion_obj.element.resize(1)
        elem = ion_obj.element[0]
        _set_if_missing(elem, "a", a)
        _set_if_missing(elem, "z_n", z_n)
        if flavor == "source":
            _set_if_missing(elem, "atoms_n", 1)
    except Exception:
        pass


def _fill_e_field(e_field, shape):
    for component_name in ("plus", "minus", "parallel"):
        try:
            component = getattr(e_field, component_name)
            component.amplitude = np.zeros(shape)
            component.phase = np.zeros(shape)
        except Exception:
            pass


def _fill_zero_ic_wave_payload(coherent_wave, input_slices, source_index, timenow,
                               waves=None, config_folder_path=None):
    radial_shape = (
        _wave_array_shape(coherent_wave, ("profiles_1d", 0, "power_density"))
        or _wave_array_shape(coherent_wave, ("profiles_1d", 0, "grid", "rho_tor_norm"))
    )
    n_rad = int(radial_shape[0]) if radial_shape else _radial_size(input_slices, waves)
    n_pol = _poloidal_size_for_wave(coherent_wave) or _poloidal_size(waves, config_folder_path)
    n_ion = _ion_count(input_slices)
    n_phi = _n_phi_values_for_wave(coherent_wave)
    if n_phi is None:
        n_phi = _n_phi_values(waves, config_folder_path)
    n_phi_count = len(n_phi)

    coherent_wave.global_quantities.resize(1)
    gq = coherent_wave.global_quantities[0]
    gq.time = timenow
    gq.frequency = _ic_frequency(input_slices, source_index)
    gq.n_phi = n_phi
    gq.power = 0.0
    gq.power_n_phi = np.zeros(n_phi_count)
    gq.current_phi = 0.0
    gq.current_phi_n_phi = np.zeros(n_phi_count)
    gq.electrons.distribution_assumption = 0
    gq.electrons.power_thermal = 0.0
    gq.electrons.power_thermal_n_phi = np.zeros(n_phi_count)
    gq.ion.resize(n_ion)
    for idx, ion in enumerate(gq.ion):
        name, z_ion, a, z_n = _ion_metadata(input_slices, idx)
        _fill_ion_metadata(ion, name, z_ion, a, z_n, flavor="wave")
        ion.power_thermal = 0.0
        ion.power_thermal_n_phi = np.zeros(n_phi_count)

    if n_rad <= 0:
        return

    coherent_wave.profiles_1d.resize(1)
    p1d = coherent_wave.profiles_1d[0]
    p1d.time = timenow
    p1d.n_phi = n_phi
    rho = np.linspace(0.0, 1.0, n_rad)
    p1d.grid.rho_tor_norm = rho
    p1d.grid.rho_tor = rho
    p1d.grid.psi = np.zeros(n_rad)
    p1d.grid.area = np.zeros(n_rad)
    p1d.grid.volume = np.zeros(n_rad)
    p1d.power_density = np.zeros(n_rad)
    p1d.power_density_n_phi = np.zeros((n_rad, n_phi_count))
    p1d.power_inside = np.zeros(n_rad)
    p1d.power_inside_n_phi = np.zeros((n_rad, n_phi_count))
    p1d.current_parallel_density = np.zeros(n_rad)
    p1d.current_parallel_density_n_phi = np.zeros((n_rad, n_phi_count))
    p1d.current_phi_inside = np.zeros(n_rad)
    p1d.current_phi_inside_n_phi = np.zeros((n_rad, n_phi_count))
    p1d.k_perpendicular = np.zeros((n_rad, n_phi_count))
    p1d.electrons.power_density_thermal = np.zeros(n_rad)
    p1d.electrons.power_density_thermal_n_phi = np.zeros((n_rad, n_phi_count))
    p1d.electrons.power_inside_thermal = np.zeros(n_rad)
    p1d.electrons.power_inside_thermal_n_phi = np.zeros((n_rad, n_phi_count))
    p1d.e_field_n_phi.resize(n_phi_count)
    for e_field in p1d.e_field_n_phi:
        _fill_e_field(e_field, (n_rad,))
    p1d.ion.resize(n_ion)
    for idx, ion in enumerate(p1d.ion):
        name, z_ion, a, z_n = _ion_metadata(input_slices, idx)
        _fill_ion_metadata(ion, name, z_ion, a, z_n, flavor="wave")
        ion.power_density_thermal = np.zeros(n_rad)
        ion.power_density_thermal_n_phi = np.zeros((n_rad, n_phi_count))
        ion.power_inside_thermal = np.zeros(n_rad)
        ion.power_inside_thermal_n_phi = np.zeros((n_rad, n_phi_count))

    if n_pol <= 0:
        return

    coherent_wave.profiles_2d.resize(1)
    p2d = coherent_wave.profiles_2d[0]
    p2d.time = timenow
    p2d.n_phi = n_phi
    shape_2d = (n_rad, n_pol)
    p2d.grid.r = np.zeros(shape_2d)
    p2d.grid.z = np.zeros(shape_2d)
    p2d.grid.rho_tor = np.zeros(shape_2d)
    p2d.grid.rho_tor_norm = np.zeros(shape_2d)
    p2d.grid.theta_geometric = np.zeros(shape_2d)
    p2d.power_density = np.zeros(shape_2d)
    p2d.power_density_n_phi = np.zeros((n_rad, n_pol, n_phi_count))
    p2d.electrons.power_density_thermal = np.zeros(shape_2d)
    p2d.electrons.power_density_thermal_n_phi = np.zeros((n_rad, n_pol, n_phi_count))
    p2d.e_field_n_phi.resize(n_phi_count)
    for e_field in p2d.e_field_n_phi:
        _fill_e_field(e_field, shape_2d)
    p2d.ion.resize(n_ion)
    for idx, ion in enumerate(p2d.ion):
        name, z_ion, a, z_n = _ion_metadata(input_slices, idx)
        _fill_ion_metadata(ion, name, z_ion, a, z_n, flavor="wave")
        ion.power_density_thermal = np.zeros(shape_2d)
        ion.power_density_thermal_n_phi = np.zeros((n_rad, n_pol, n_phi_count))


def _zero_field_like(obj, field_name):
    try:
        value = getattr(obj, field_name)
        arr = np.asarray(value)
        if arr.shape:
            setattr(obj, field_name, np.zeros_like(arr))
        elif getattr(value, 'has_value', False):
            setattr(obj, field_name, 0.0)
    except Exception:
        pass


def _zero_wave_particle_power(particle):
    for field_name in (
        "power_thermal",
        "power_thermal_n_phi",
        "power_density_thermal",
        "power_density_thermal_n_phi",
        "power_inside_thermal",
        "power_inside_thermal_n_phi",
    ):
        _zero_field_like(particle, field_name)


def _zero_e_field(e_field):
    for component_name in ("plus", "minus", "parallel"):
        try:
            component = getattr(e_field, component_name)
            _zero_field_like(component, "amplitude")
            _zero_field_like(component, "phase")
        except Exception:
            pass


def _zero_existing_wave_payload(coherent_wave, timenow):
    for gq in getattr(coherent_wave, "global_quantities", []):
        try:
            gq.time = timenow
        except Exception:
            pass
        for field_name in (
            "power",
            "power_n_phi",
            "current_phi",
            "current_phi_n_phi",
        ):
            _zero_field_like(gq, field_name)
        try:
            _zero_wave_particle_power(gq.electrons)
        except Exception:
            pass
        for ion in getattr(gq, "ion", []):
            _zero_wave_particle_power(ion)

    for p1d in getattr(coherent_wave, "profiles_1d", []):
        try:
            p1d.time = timenow
        except Exception:
            pass
        for field_name in (
            "power_density",
            "power_density_n_phi",
            "power_inside",
            "power_inside_n_phi",
            "current_parallel_density",
            "current_parallel_density_n_phi",
            "current_phi_inside",
            "current_phi_inside_n_phi",
        ):
            _zero_field_like(p1d, field_name)
        try:
            _zero_wave_particle_power(p1d.electrons)
        except Exception:
            pass
        for ion in getattr(p1d, "ion", []):
            _zero_wave_particle_power(ion)
        for e_field in getattr(p1d, "e_field_n_phi", []):
            _zero_e_field(e_field)

    for p2d in getattr(coherent_wave, "profiles_2d", []):
        try:
            p2d.time = timenow
        except Exception:
            pass
        for field_name in (
            "power_density",
            "power_density_n_phi",
        ):
            _zero_field_like(p2d, field_name)
        try:
            _zero_wave_particle_power(p2d.electrons)
        except Exception:
            pass
        for ion in getattr(p2d, "ion", []):
            _zero_wave_particle_power(ion)
        for e_field in getattr(p2d, "e_field_n_phi", []):
            _zero_e_field(e_field)


def _fill_zero_wave_slot(coherent_wave, source_kind, source_index, input_slices,
                         timenow, waves=None, config_folder_path=None):
    if source_kind == "ic":
        _set_code(coherent_wave.identifier.type, "IC", 3)
        _set_code(coherent_wave.wave_solver_type, "IC", 2)
        coherent_wave.identifier.antenna_name = _ic_antenna_name(
            input_slices.get("ic_antennas"), source_index)
        coherent_wave.identifier.index_in_antenna = source_index + 1
        _fill_zero_ic_wave_payload(
            coherent_wave, input_slices, source_index, timenow,
            waves=waves, config_folder_path=config_folder_path,
        )
        return

    # EC (and any future source_kind): minimal global_quantities placeholder.
    # profiles_1d/2d are intentionally left empty so the first real torbeam
    # output establishes the HDF5 schema for those arrays.
    _set_code(coherent_wave.identifier.type, "EC", 1)
    _set_code(coherent_wave.wave_solver_type, None, 1)
    coherent_wave.identifier.antenna_name = _ec_beam_name(
        input_slices.get("ec_launchers"), source_index)
    _zero_existing_wave_payload(coherent_wave, timenow)
    try:
        coherent_wave.global_quantities.resize(1)
        gq = coherent_wave.global_quantities[0]
        gq.time = timenow
        gq.power = 0.0
        gq.current_phi = 0.0
        gq.n_phi = np.zeros(1, dtype=np.int32)
        gq.power_n_phi = np.zeros(1)
        gq.current_phi_n_phi = np.zeros(1)
    except Exception:
        pass


def _expected_wave_slots(input_slices, param_process):
    expected = []
    if _process_is_selected(param_process, "ec_wave_solver"):
        n_ec = _safe_len(getattr(input_slices.get("ec_launchers"), "beam", []))
        expected.extend(("ec", i) for i in range(n_ec))
    if _process_is_selected(param_process, "ic_wave_solver"):
        n_ic = _safe_len(getattr(input_slices.get("ic_antennas"), "antenna", []))
        expected.extend(("ic", i) for i in range(n_ic))
    return expected


def _ec_total_power(ec_launchers_ids):
    if ec_launchers_ids is None:
        return 0.0
    total = 0.0
    try:
        for beam in ec_launchers_ids.beam:
            if hasattr(beam.power_launched, 'data') and len(beam.power_launched.data) > 0:
                total += float(beam.power_launched.data[0])
            elif hasattr(beam, 'power_launched') and beam.power_launched.has_value:
                total += float(np.asarray(beam.power_launched).flat[0])
    except Exception:
        return 0.0
    return total


def _ic_total_power(ic_antennas_ids):
    if ic_antennas_ids is None:
        return 0.0
    total = 0.0
    try:
        for antenna in ic_antennas_ids.antenna:
            pl = antenna.power_launched
            if hasattr(pl, 'data') and len(pl.data) > 0:
                total += float(pl.data[0])
    except Exception:
        return 0.0
    return total


def _active_wave_sources(input_slices):
    return {
        "ec": abs(_ec_total_power(input_slices.get("ec_launchers"))) > 0.0,
        "ic": abs(_ic_total_power(input_slices.get("ic_antennas"))) > 0.0,
    }


def _ensure_waves_placeholders(input_slices, output_ids, param_process, timenow,
                               config_folder_path=None):
    expected = _expected_wave_slots(input_slices, param_process)
    if not expected:
        return

    waves = _ensure_output_slice(output_ids, "waves", timenow)
    current_len = _safe_len(waves.coherent_wave)

    # keep=True preserves existing elements and only appends new empty slots.
    if current_len < len(expected):
        waves.coherent_wave.resize(len(expected), keep=True)

    active_sources = _active_wave_sources(input_slices)

    for slot_index, (source_kind, source_index) in enumerate(expected):
        slot_was_missing = slot_index >= current_len
        source_is_inactive = not active_sources.get(source_kind, False)
        if not slot_was_missing and not source_is_inactive:
            continue
        _fill_zero_wave_slot(
            waves.coherent_wave[slot_index],
            source_kind,
            source_index,
            input_slices,
            timenow,
            waves=waves,
            config_folder_path=config_folder_path,
        )


def _source_name(source):
    try:
        return str(source.identifier.name).strip().lower()
    except Exception:
        return ""


def _ensure_source_global_quantities(source, timenow):
    try:
        if _safe_len(source.global_quantities) == 0:
            source.global_quantities.resize(1)
        gq = source.global_quantities[0]
    except Exception:
        return

    try:
        gq.time = timenow
    except Exception:
        pass

    for field_name in ("power", "current_parallel", "total_ion_power"):
        _set_zero_if_missing(gq, field_name)

    try:
        _set_zero_if_missing(gq.electrons, "power")
    except Exception:
        pass


def _existing_source_radial_size(source):
    """Return nrho from a source's existing profiles_1d, or 0 if absent."""
    try:
        existing = source.profiles_1d[0].electrons.energy
        if getattr(existing, 'has_value', False):
            shape = np.asarray(existing).shape
            if shape and shape[0] > 0:
                return int(shape[0])
    except Exception:
        pass
    return 0


def _source_radial_size(source, sibling_sources, input_slices, config_folder_path):
    """Pick nrho for an IC core_sources placeholder.

    Priority: this source's own profiles_1d > any sibling source's profiles_1d
    (typically EC, written by hcd2core_sources at the same timestep) >
    hcd2core_sources XML radial_resolution > core_profiles/equilibrium grid > 0.
    """
    own = _existing_source_radial_size(source)
    if own > 0:
        return own

    for sibling in sibling_sources:
        if sibling is source:
            continue
        sibling_nrho = _existing_source_radial_size(sibling)
        if sibling_nrho > 0:
            return sibling_nrho

    nrho = _xml_int(
        config_folder_path,
        "source/fill_core_sources/input_hcd2core_sources.xml",
        "radial_resolution",
        None,
    )
    if nrho and nrho > 0:
        return int(nrho)

    return _radial_size(input_slices, waves=None)


def _ensure_source_profiles_1d(source, sibling_sources, input_slices, timenow,
                               config_folder_path):
    """Ensure profiles_1d[0] has the schema CYRANO writes.

    Only used for IC sources: avoids creating empty profiles_1d for EC where
    torbeam/hcd2core_sources establishes the schema with the real nrho.
    Without this, CYRANO's first IC-on slice would be the first time
    ion[].energy is written and HDF5 only allocates that field for
    IC-active timesteps (causing readback errors at IC-off times).

    Never overwrites CYRANO-written values: every field write is gated by
    `has_value` checks, and AoS resizes use keep=True.
    """
    nrho = _source_radial_size(source, sibling_sources, input_slices,
                               config_folder_path)
    if nrho <= 0:
        return

    try:
        if _safe_len(source.profiles_1d) == 0:
            source.profiles_1d.resize(1)
        p1d = source.profiles_1d[0]
    except Exception:
        return

    try:
        p1d.time = timenow
    except Exception:
        pass

    rho = np.linspace(0.0, 1.0, nrho)
    zeros = np.zeros(nrho)

    for field_name, value in (
        ("rho_tor_norm", rho),
        ("rho_tor", rho),
        ("rho_pol_norm", rho.copy()),
        ("psi", zeros.copy()),
        ("area", zeros.copy()),
        ("surface", zeros.copy()),
        ("volume", zeros.copy()),
    ):
        _set_if_missing(p1d.grid, field_name, value)

    _set_if_missing(p1d, "j_parallel", zeros.copy())
    try:
        _set_if_missing(p1d.electrons, "energy", zeros.copy())
    except Exception:
        pass

    n_ion = _ion_count(input_slices)
    if n_ion <= 0:
        return

    try:
        if _safe_len(p1d.ion) < n_ion:
            p1d.ion.resize(n_ion, keep=True)
    except Exception:
        return

    for idx, ion in enumerate(p1d.ion):
        name, z_ion, a, z_n = _ion_metadata(input_slices, idx)
        _fill_ion_metadata(ion, name, z_ion, a, z_n, flavor="source")
        try:
            if not _has_imas_value(ion.energy):
                ion.energy = zeros.copy()
        except Exception:
            pass


def _fill_zero_source_slot(source, source_kind, timenow,
                           sibling_sources=(), input_slices=None,
                           config_folder_path=None):
    if source_kind == "ec":
        source.identifier.name = "ec"
        source.identifier.index = 3
    elif source_kind == "ic":
        source.identifier.name = "ic"
        source.identifier.index = 5
    _ensure_source_global_quantities(source, timenow)
    if source_kind == "ic" and input_slices is not None:
        _ensure_source_profiles_1d(
            source, sibling_sources, input_slices, timenow, config_folder_path)


def _expected_source_names(param_process):
    expected = []
    if _process_is_selected(param_process, "ec_wave_solver"):
        expected.append("ec")
    if _process_is_selected(param_process, "ic_wave_solver"):
        expected.append("ic")
    return expected


def _ensure_core_sources_placeholders(input_slices, output_ids, param_process,
                                      timenow, config_folder_path=None):
    if not _process_is_selected(param_process, "fill_core_sources"):
        return

    expected = _expected_source_names(param_process)
    if not expected:
        return

    core_sources = _ensure_output_slice(output_ids, "core_sources", timenow)
    names = [_source_name(source) for source in core_sources.source]
    blank_indices = [idx for idx, name in enumerate(names) if not name]

    for source_kind in expected:
        if source_kind in names:
            continue
        if blank_indices:
            idx = blank_indices.pop(0)
        else:
            idx = _safe_len(core_sources.source)
            core_sources.source.resize(idx + 1, keep=True)
            names.append("")
        _fill_zero_source_slot(
            core_sources.source[idx], source_kind, timenow,
            sibling_sources=core_sources.source,
            input_slices=input_slices,
            config_folder_path=config_folder_path,
        )
        names[idx] = source_kind

    for source, name in zip(core_sources.source, names):
        _ensure_source_global_quantities(source, timenow)
        if name == "ic":
            _ensure_source_profiles_1d(
                source, core_sources.source, input_slices, timenow,
                config_folder_path)


def stabilize_selected_hcd_outputs(input_slices, output_ids, param_process,
                                    timenow, config_folder_path=None):
    """Fill placeholder slots for outputs the workflow is configured to produce."""
    if param_process is None or timenow is None:
        return
    _ensure_waves_placeholders(
        input_slices, output_ids, param_process, timenow,
        config_folder_path=config_folder_path,
    )
    _ensure_core_sources_placeholders(
        input_slices, output_ids, param_process, timenow,
        config_folder_path=config_folder_path,
    )
