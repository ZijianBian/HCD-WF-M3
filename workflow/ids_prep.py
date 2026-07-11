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
    import yaml
except ImportError:
    yaml = None

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

    Some ITER scenarios leave global_quantities.psi_axis as the
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


def _eq_fill_rho_tor_from_flux(eq, ts):
    """Fill profiles_1d.rho_tor from toroidal flux when only rho_norm exists.

    FoPla's input writer expects the dimensional toroidal-flux radius. Some
    Some ITER equilibrium slices provide rho_tor_norm and phi, but leave
    rho_tor empty; the derived radius follows the IMAS toroidal-flux
    definition and uses |B0| so the sign convention of phi/B0 is harmless.
    """
    if not hasattr(ts, 'profiles_1d'):
        return

    p1d = ts.profiles_1d
    try:
        if p1d.rho_tor.has_value and len(p1d.rho_tor) > 0:
            return
    except Exception:
        try:
            if len(p1d.rho_tor) > 0:
                return
        except Exception:
            pass

    if not (
        getattr(p1d.rho_tor_norm, 'has_value', False)
        and len(p1d.rho_tor_norm) > 0
        and getattr(p1d.phi, 'has_value', False)
        and len(p1d.phi) > 0
        and getattr(eq.vacuum_toroidal_field.b0, 'has_value', False)
        and len(eq.vacuum_toroidal_field.b0) > 0
    ):
        return

    try:
        rho_norm = np.asarray(p1d.rho_tor_norm, dtype=float)
        phi = np.asarray(p1d.phi, dtype=float)
        b0 = abs(float(np.asarray(eq.vacuum_toroidal_field.b0, dtype=float).ravel()[0]))

        if rho_norm.size == 0 or phi.size != rho_norm.size or not np.isfinite(b0) or b0 <= 0:
            return

        finite_phi = np.isfinite(phi) & (np.abs(phi) < 1.e35)
        if not np.any(finite_phi):
            return

        phi_axis = phi[0] if finite_phi[0] else phi[np.where(finite_phi)[0][0]]
        delta_phi = np.abs(phi - phi_axis)
        rho_tor = np.sqrt(np.maximum(delta_phi, 0.0) / (np.pi * b0))

        if (
            np.any(~np.isfinite(rho_tor))
            or not np.isfinite(rho_tor[-1])
            or rho_tor[-1] <= 0.0
            or np.any(np.diff(rho_tor) < -1.e-8)
        ):
            edge_delta_phi = np.nanmax(delta_phi[finite_phi])
            if not np.isfinite(edge_delta_phi) or edge_delta_phi <= 0.0:
                return
            rho_tor_edge = np.sqrt(edge_delta_phi / (np.pi * b0))
            rho_tor = rho_norm * rho_tor_edge

        p1d.rho_tor = rho_tor
        print(f"  [equilibrium] Filled rho_tor from toroidal flux for FoPla "
              f"({rho_tor.size} points, edge={rho_tor[-1]:.4g} m)", flush=True)
    except Exception as e:
        print(f"  [equilibrium] WARNING: Could not fill rho_tor from flux: {e}", flush=True)


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
    _eq_fill_rho_tor_from_flux(eq, ts)

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


def _numeric_array_or_none(obj, field_name):
    try:
        value = getattr(obj, field_name)
    except Exception:
        return None
    try:
        if getattr(value, "has_value", True) is False:
            return None
    except Exception:
        pass
    try:
        arr = np.asarray(value)
        if arr.dtype.kind not in "biufc":
            return None
        return arr
    except Exception:
        try:
            return np.asarray(float(value))
        except Exception:
            return None


def _valid_profile_array(values, expected_size=None):
    try:
        array = np.asarray(values, dtype=float)
    except Exception:
        return None
    if array.size == 0:
        return None
    if expected_size is not None and array.size != expected_size:
        return None
    return np.where(np.isfinite(array) & (np.abs(array) < 1.0e30), array, 0.0)


def _add_profile_to_grid(total, source_grid, values, target_grid):
    if values is None or source_grid is None:
        return total
    if total is None:
        total = np.zeros_like(target_grid, dtype=float)
    if len(source_grid) == len(target_grid) and np.allclose(source_grid, target_grid):
        total += values
    else:
        total += np.interp(target_grid, source_grid, values, left=0.0, right=0.0)
    return total


def _set_array_or_scalar(obj, field_name, value):
    try:
        arr = np.asarray(value)
        if arr.shape == ():
            setattr(obj, field_name, float(arr))
        else:
            setattr(obj, field_name, arr)
    except Exception:
        pass


def _weighted_sum_field(target, sources, field_name, weights):
    arrays = [_numeric_array_or_none(source, field_name) for source in sources]
    if any(arr is None for arr in arrays):
        return
    result = np.zeros_like(arrays[0], dtype=float)
    for weight, arr in zip(weights, arrays):
        result = result + float(weight) * np.asarray(arr, dtype=float)
    _set_array_or_scalar(target, field_name, result)


def _mode_axis(arr):
    arr = np.asarray(arr)
    for axis, size in enumerate(arr.shape):
        if size == 1:
            return axis
    return 0


def _single_mode_slice(arr, axis):
    arr = np.asarray(arr)
    if arr.shape == ():
        return arr
    if arr.shape[axis] == 1:
        return np.take(arr, 0, axis=axis)
    return arr


def _mode_stack_field(target, sources, field_name, weights, scale=True):
    arrays = [_numeric_array_or_none(source, field_name) for source in sources]
    if any(arr is None for arr in arrays):
        return
    first = np.asarray(arrays[0])
    if first.shape == ():
        values = [
            (float(weight) if scale else 1.0) * float(np.asarray(arr))
            for weight, arr in zip(weights, arrays)
        ]
        setattr(target, field_name, np.asarray(values, dtype=float))
        return

    axis = _mode_axis(first)
    slices = []
    for weight, arr in zip(weights, arrays):
        mode_data = np.asarray(_single_mode_slice(arr, axis), dtype=float)
        if scale:
            mode_data = float(weight) * mode_data
        slices.append(mode_data)
    try:
        setattr(target, field_name, np.stack(slices, axis=axis))
    except Exception:
        pass


def _merge_particle_power(target, sources, weights):
    for field_name in (
        "power_thermal",
        "power_density_thermal",
        "power_inside_thermal",
    ):
        _weighted_sum_field(target, sources, field_name, weights)
    for field_name in (
        "power_thermal_n_phi",
        "power_density_thermal_n_phi",
        "power_inside_thermal_n_phi",
    ):
        _mode_stack_field(target, sources, field_name, weights, scale=True)


def _merge_e_field_components(target_component, source_components, weight):
    for field_name in ("amplitude", "phase"):
        arr = _numeric_array_or_none(source_components, field_name)
        if arr is None:
            continue
        if field_name == "amplitude":
            arr = np.sqrt(float(weight)) * np.asarray(arr, dtype=float)
        _set_array_or_scalar(target_component, field_name, arr)


def _merge_e_field_n_phi(target_aos, source_aos_list, weights):
    try:
        target_aos.resize(len(source_aos_list))
    except Exception:
        return
    for idx, (source_aos, weight) in enumerate(zip(source_aos_list, weights)):
        if _safe_len(source_aos) == 0:
            continue
        source_field = source_aos[0]
        target_field = target_aos[idx]
        for component_name in ("plus", "minus", "parallel"):
            try:
                _merge_e_field_components(
                    getattr(target_field, component_name),
                    getattr(source_field, component_name),
                    weight,
                )
            except Exception:
                pass


def _merge_wave_global_quantities(target_gq, source_gqs, n_phi, weights):
    target_gq.n_phi = n_phi
    for field_name in ("power", "current_phi"):
        _weighted_sum_field(target_gq, source_gqs, field_name, weights)
    _mode_stack_field(target_gq, source_gqs, "power_n_phi", weights, scale=True)
    _mode_stack_field(target_gq, source_gqs, "current_phi_n_phi", weights, scale=True)

    try:
        _merge_particle_power(
            target_gq.electrons,
            [source.electrons for source in source_gqs],
            weights,
        )
    except Exception:
        pass

    try:
        n_ion = min(_safe_len(target_gq.ion), *[_safe_len(source.ion) for source in source_gqs])
    except Exception:
        n_ion = 0
    for ion_index in range(n_ion):
        _merge_particle_power(
            target_gq.ion[ion_index],
            [source.ion[ion_index] for source in source_gqs],
            weights,
        )


def _merge_wave_profiles_1d(target_p1d, source_p1ds, n_phi, weights):
    target_p1d.n_phi = n_phi
    for field_name in (
        "power_density",
        "power_inside",
        "current_parallel_density",
        "current_phi_inside",
    ):
        _weighted_sum_field(target_p1d, source_p1ds, field_name, weights)
    for field_name in (
        "power_density_n_phi",
        "power_inside_n_phi",
        "current_parallel_density_n_phi",
        "current_phi_inside_n_phi",
    ):
        _mode_stack_field(target_p1d, source_p1ds, field_name, weights, scale=True)
    _mode_stack_field(target_p1d, source_p1ds, "k_perpendicular", weights, scale=False)

    try:
        _merge_particle_power(
            target_p1d.electrons,
            [source.electrons for source in source_p1ds],
            weights,
        )
    except Exception:
        pass

    try:
        n_ion = min(_safe_len(target_p1d.ion), *[_safe_len(source.ion) for source in source_p1ds])
    except Exception:
        n_ion = 0
    for ion_index in range(n_ion):
        _merge_particle_power(
            target_p1d.ion[ion_index],
            [source.ion[ion_index] for source in source_p1ds],
            weights,
        )

    _merge_e_field_n_phi(
        target_p1d.e_field_n_phi,
        [source.e_field_n_phi for source in source_p1ds],
        weights,
    )


def _merge_wave_profiles_2d(target_p2d, source_p2ds, n_phi, weights):
    target_p2d.n_phi = n_phi
    _weighted_sum_field(target_p2d, source_p2ds, "power_density", weights)
    _mode_stack_field(target_p2d, source_p2ds, "power_density_n_phi", weights, scale=True)

    try:
        _weighted_sum_field(
            target_p2d.electrons,
            [source.electrons for source in source_p2ds],
            "power_density_thermal",
            weights,
        )
        _mode_stack_field(
            target_p2d.electrons,
            [source.electrons for source in source_p2ds],
            "power_density_thermal_n_phi",
            weights,
            scale=True,
        )
    except Exception:
        pass

    try:
        n_ion = min(_safe_len(target_p2d.ion), *[_safe_len(source.ion) for source in source_p2ds])
    except Exception:
        n_ion = 0
    for ion_index in range(n_ion):
        _weighted_sum_field(
            target_p2d.ion[ion_index],
            [source.ion[ion_index] for source in source_p2ds],
            "power_density_thermal",
            weights,
        )
        _mode_stack_field(
            target_p2d.ion[ion_index],
            [source.ion[ion_index] for source in source_p2ds],
            "power_density_thermal_n_phi",
            weights,
            scale=True,
        )

    _merge_e_field_n_phi(
        target_p2d.e_field_n_phi,
        [source.e_field_n_phi for source in source_p2ds],
        weights,
    )


def merge_ic_wave_modes(mode_waves, n_phi_values, weights):
    """Merge single-mode CYRANO `waves` outputs into one IC coherent-wave slot.

    CYRANO is run once per toroidal mode at the full slice power. This helper
    performs the incoherent power/current sum by scaling each single-mode
    output by its normalized weight, while preserving per-mode diagnostics on
    the `n_phi` sub-axis.
    """
    if not mode_waves:
        raise ValueError("mode_waves must contain at least one waves IDS")
    if len(mode_waves) != len(n_phi_values) or len(mode_waves) != len(weights):
        raise ValueError("mode_waves, n_phi_values and weights must have the same length")

    weights = np.asarray(weights, dtype=float)
    total_weight = float(weights.sum())
    if total_weight <= 0.0:
        raise ValueError("mode weights must sum to a positive value")
    weights = weights / total_weight
    n_phi = np.asarray(n_phi_values, dtype=np.int32)

    merged = copy.deepcopy(mode_waves[0])
    try:
        merged.ids_properties.homogeneous_time = 1
    except Exception:
        pass

    source_waves = [waves.coherent_wave[0] for waves in mode_waves]
    try:
        merged.coherent_wave.resize(1, keep=True)
    except Exception:
        pass
    target_wave = merged.coherent_wave[0]

    if _safe_len(target_wave.global_quantities) and all(_safe_len(w.global_quantities) for w in source_waves):
        _merge_wave_global_quantities(
            target_wave.global_quantities[0],
            [wave.global_quantities[0] for wave in source_waves],
            n_phi,
            weights,
        )

    if _safe_len(target_wave.profiles_1d) and all(_safe_len(w.profiles_1d) for w in source_waves):
        _merge_wave_profiles_1d(
            target_wave.profiles_1d[0],
            [wave.profiles_1d[0] for wave in source_waves],
            n_phi,
            weights,
        )

    if _safe_len(target_wave.profiles_2d) and all(_safe_len(w.profiles_2d) for w in source_waves):
        _merge_wave_profiles_2d(
            target_wave.profiles_2d[0],
            [wave.profiles_2d[0] for wave in source_waves],
            n_phi,
            weights,
        )

    return merged


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


def _signal_value_at_time(signal, time=None, default=0.0):
    """Value of a time-dependent IMAS signal node (`.data` / `.time`).

    Picks the sample nearest `time` when both `time` and a matching time
    base are available; otherwise falls back to the first value.
    """
    try:
        data = np.asarray(signal.data, dtype=float).ravel()
    except Exception:
        return default
    if data.size == 0:
        return default
    if time is None:
        return float(data[0])
    try:
        tarr = np.asarray(getattr(signal, "time", []), dtype=float).ravel()
        if tarr.size == data.size and tarr.size > 0:
            return float(data[int(np.argmin(np.abs(tarr - time)))])
    except Exception:
        pass
    return float(data[0])


def _strap_phi(strap, default=0.0):
    """Toroidal angle [rad] of a strap centre, from `outline.phi`."""
    try:
        phi = np.asarray(strap.outline.phi, dtype=float).ravel()
        if phi.size > 0:
            return float(np.mean(phi))
    except Exception:
        pass
    return default


def _ic_antenna_straps(ic_antennas, antenna_index=0, time=None):
    """List of `(phase [rad], phi [rad])` for every strap of an IC antenna."""
    straps = []
    try:
        antenna = ic_antennas.antenna[antenna_index]
    except Exception:
        return straps
    try:
        modules = list(antenna.module)
    except Exception:
        modules = []
    for module in modules:
        try:
            module_straps = list(module.strap)
        except Exception:
            module_straps = []
        for strap in module_straps:
            phase = _signal_value_at_time(getattr(strap, "phase", None), time, 0.0)
            straps.append((phase, _strap_phi(strap, 0.0)))
    return straps


def ic_antenna_n_phi_weights(ic_antennas, antenna_index=0, time=None,
                             n_values=None, n_max=80):
    """Toroidal-mode (`n_phi`) power-weight spectrum of an IC antenna.

    Builds the array factor

        w_n = |sum_j exp(i * phase_j - i * n * phi_j)|^2

    from the strap phase and toroidal position stored in the `ic_antennas`
    IDS, where `j` runs over all straps of all modules of the antenna.
    `w_n` is the relative power launched into toroidal mode `n`; the net
    current driven by a multi-mode run is the `w_n`-weighted sum of
    single-mode CYRANO results.

    This is a pure function: it neither runs CYRANO nor touches the
    database. The multi-mode CYRANO loop belongs in the driver layer.

    Note: this models only the strap-phase array factor. The finite strap
    toroidal width (`width_tor`) and per-strap current amplitude are not
    modelled here; add them before a final quantitative spectrum if the
    width/amplitude data are needed.

    Sign convention: the array factor uses `exp(i*phase_j - i*n*phi_j)`.
    For symmetric (dipole) phasing this is harmless since `w(+n) == w(-n)`,
    but for asymmetric current-drive phasing the +n/-n split depends on
    this convention -- reconcile it with the CYRANO `Ntor` and IMAS
    `waves.n_phi` sign conventions before wiring up the driver loop.

    Returns `(n_phi, weight)` as numpy arrays; `weight` sums to 1 (or is
    all-zero only if no strap data is available and `n=0` is not sampled).
    """
    straps = _ic_antenna_straps(ic_antennas, antenna_index, time)
    if n_values is None:
        n_values = np.arange(-int(n_max), int(n_max) + 1, dtype=np.int32)
    else:
        n_values = np.asarray(n_values, dtype=np.int32)

    weight = np.zeros(len(n_values), dtype=float)
    if not straps:
        # No strap data: put all weight on n=0 if it is sampled.
        zero_idx = np.where(n_values == 0)[0]
        if zero_idx.size:
            weight[zero_idx[0]] = 1.0
        return n_values, weight

    phases = np.array([p for p, _ in straps], dtype=float)
    phis = np.array([f for _, f in straps], dtype=float)
    for k, n in enumerate(n_values):
        amp = np.sum(np.exp(1j * (phases - n * phis)))
        weight[k] = float(np.abs(amp) ** 2)

    total = weight.sum()
    if total > 0:
        weight = weight / total
    return n_values, weight


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


def _wave_array_values(coherent_wave, path, dtype=None):
    """Return a populated wave array, preserving its values and shape."""
    try:
        value = coherent_wave
        for part in path:
            value = value[part] if isinstance(part, int) else getattr(value, part)
        if not getattr(value, "has_value", False):
            return None
        array = np.asarray(value, dtype=dtype)
        if array.size == 0:
            return None
        return array.copy()
    except Exception:
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
    # The configured spectrum is authoritative for inactive-IC placeholders.
    # In particular, an EC-only output still contains a one-element EC n_phi
    # axis; using that axis first would shrink a configured two-mode IC slot.
    configured_n_phi = _configured_toroidal_n_phi_values(config_folder_path)
    if configured_n_phi is not None:
        return configured_n_phi

    for path in (
        ("global_quantities", 0, "n_phi"),
        ("profiles_1d", 0, "n_phi"),
        ("profiles_2d", 0, "n_phi"),
    ):
        try:
            coherent_waves = list(waves.coherent_wave)
        except Exception:
            coherent_waves = []
        # Prefer an existing IC slot, then fall back to any populated slot.
        for coherent_wave in sorted(
            coherent_waves,
            key=lambda wave: 0 if _wave_is_ic(wave) else 1,
        ):
            values = _wave_array_values(coherent_wave, path, dtype=np.int32)
            if values is not None:
                return values.reshape(-1)

    ntor = _xml_int(config_folder_path, "ICRH/ic_wave_solver/input_cyrano.xml", "Ntor", 0)
    if ntor:
        # Accept any nonzero Ntor, including negative single toroidal modes
        # (e.g. Ntor=-35) so symmetric/negative-n spectra are not lost.
        return np.array([ntor], dtype=np.int32)
    return np.zeros(1, dtype=np.int32)


def _configured_toroidal_n_phi_values(config_folder_path):
    if yaml is None or not config_folder_path:
        return None
    path = os.path.join(config_folder_path, "ic_toroidal_modes.yaml")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            data = yaml.safe_load(file_obj) or {}
    except Exception:
        return None
    if data.get("enabled", True) is False:
        return None

    values = []
    for mode in data.get("modes", []):
        try:
            weight = float(mode.get("weight", 1.0))
            n_phi = int(mode["n_phi"])
        except (TypeError, ValueError, KeyError):
            continue
        if weight > 0.0:
            values.append(n_phi)
    if not values:
        return None
    return np.asarray(values, dtype=np.int32)


def _n_phi_values_for_wave(coherent_wave):
    for path in (
        ("global_quantities", 0, "n_phi"),
        ("profiles_1d", 0, "n_phi"),
        ("profiles_2d", 0, "n_phi"),
    ):
        values = _wave_array_values(coherent_wave, path, dtype=np.int32)
        if values is not None:
            return values.reshape(-1)
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
    p1d.grid.rho_pol_norm = rho
    p1d.grid.psi = np.zeros(n_rad)
    p1d.grid.area = np.zeros(n_rad)
    p1d.grid.surface = np.zeros(n_rad)
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
    # Keep Torbeam ray geometry so consecutive DD4 slices retain an identical
    # HDF5 schema, but an inactive EC source must not carry power deposited by
    # the last active slice.  Torbeam stores that power below beam_tracing in
    # addition to global_quantities/profiles_1d.
    for tracing in getattr(coherent_wave, "beam_tracing", []):
        try:
            tracing.time = timenow
        except Exception:
            pass
        for beam in getattr(tracing, "beam", []):
            _zero_field_like(beam, "power_initial")
            try:
                _zero_field_like(beam.electrons, "power")
            except Exception:
                pass
            for ion in getattr(beam, "ion", []):
                _zero_field_like(ion, "power")

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


def _fill_zero_ec_wave_payload(coherent_wave, input_slices, timenow,
                               waves=None, config_folder_path=None):
    """Create the 1D Torbeam schema for an inactive EC beam."""
    n_rad = _xml_int(
        config_folder_path,
        "ECRH/ec_wave_solver/input_torbeam.xml",
        "nradial",
        None,
    )
    if not n_rad or n_rad <= 0:
        radial_shape = (
            _wave_array_shape(coherent_wave, ("profiles_1d", 0, "power_density"))
            or _first_wave_array_shape(waves, ("profiles_1d", 0, "power_density"))
        )
        n_rad = int(radial_shape[0]) if radial_shape else _radial_size(input_slices, waves)
    if not n_rad or n_rad <= 0:
        return

    coherent_wave.profiles_1d.resize(1)
    profile = coherent_wave.profiles_1d[0]
    profile.time = timenow
    rho = np.linspace(0.0, 1.0, int(n_rad))
    zeros = np.zeros(int(n_rad))
    profile.grid.rho_tor_norm = rho
    profile.grid.rho_tor = rho
    profile.grid.rho_pol_norm = rho
    profile.grid.psi = zeros.copy()
    profile.grid.volume = zeros.copy()
    profile.grid.area = zeros.copy()
    profile.grid.surface = zeros.copy()
    profile.grid.psi_magnetic_axis = 0.0
    profile.grid.psi_boundary = 0.0
    profile.power_density = zeros.copy()
    profile.current_parallel_density = zeros.copy()
    profile.electrons.power_density_thermal = zeros.copy()


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

    # EC placeholder follows the Torbeam 1D output contract so inactive slices
    # retain the actor-established radial shape.
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
    _fill_zero_ec_wave_payload(
        coherent_wave,
        input_slices,
        timenow,
        waves=waves,
        config_folder_path=config_folder_path,
    )


_WAVE_PROCESS_KINDS = {
    "ec_wave_solver": "ec",
    "ic_wave_solver": "ic",
}


def _selected_wave_kinds(param_process):
    """Return selected source kinds in configuration order, without coupling."""
    try:
        process_names = list(param_process)
    except Exception:
        process_names = []

    selected = []
    for process_name in process_names:
        kind = _WAVE_PROCESS_KINDS.get(str(process_name))
        if (kind is not None
                and kind not in selected
                and _process_is_selected(param_process, process_name)):
            selected.append(kind)

    # Some mapping-like parameter containers do not expose iteration.  This
    # fallback discovers selection only; actor output still determines layout.
    if not process_names:
        for process_name, kind in _WAVE_PROCESS_KINDS.items():
            if _process_is_selected(param_process, process_name):
                selected.append(kind)
    return selected


def _selected_wave_counts(input_slices, param_process):
    counts = {}
    for kind in _selected_wave_kinds(param_process):
        if kind == "ec":
            counts[kind] = _safe_len(
                getattr(input_slices.get("ec_launchers"), "beam", []))
        elif kind == "ic":
            counts[kind] = _safe_len(
                getattr(input_slices.get("ic_antennas"), "antenna", []))
    return counts


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


def _selected_active_wave_sources(input_slices, param_process):
    active = _active_wave_sources(input_slices)
    selected = set(_selected_wave_kinds(param_process))
    return {kind: active.get(kind, False) for kind in selected}


def _wave_source_kind(coherent_wave):
    if _wave_is_ic(coherent_wave):
        return "ic"
    try:
        type_name = _code_field_name(coherent_wave.identifier.type)
        type_index = _code_field_index(coherent_wave.identifier.type)
        solver_name = _code_field_name(coherent_wave.wave_solver_type)
    except Exception:
        return None
    if "ec" in type_name or type_index == 1 or "ec" in solver_name:
        return "ec"
    return None


# Actor-created wave subtrees (notably Torbeam beam_tracing/profiles_2d) are
# much richer than a hand-built inactive placeholder.  Cache serialized, full
# IDS snapshots instead of detached IMAS structures: deepcopying an AoS element
# breaks its link to the parent IDS and can produce an incomplete HDF5 schema.
_WAVE_SCHEMA_TEMPLATES = {}
_CORE_SOURCES_SCHEMA_TEMPLATES = {}


def _wave_template_key(config_folder_path):
    if config_folder_path:
        return os.path.abspath(config_folder_path)
    return "__default__"


def _serialize_ids_snapshot(ids_data):
    """Return an immutable full-IDS snapshot, or ``None`` if unsupported."""
    try:
        payload = ids_data.serialize()
    except Exception:
        return None
    return payload if isinstance(payload, bytes) else bytes(payload)


def _deserialize_ids_snapshot(ids_name, payload):
    """Build a fresh, parent-linked IDS from a serialized snapshot."""
    if not payload:
        return None
    try:
        restored = _create_ids(ids_name)
        restored.deserialize(payload)
        return restored
    except Exception:
        return None


def _schema_richness(node, payload=None):
    """Rank snapshots by populated schema, then data size.

    Rich active actor output must never be replaced by a later sparse result.
    Counting assigned leaves is more useful than payload size alone because it
    rewards paths such as ``beam_tracing`` and top-level vacuum-field data.
    """
    leaves = 0
    values = 0
    try:
        for leaf in _iter_nonempty_ids_leaves(node):
            leaves += 1
            try:
                values += int(np.asarray(leaf.value).size)
            except Exception:
                pass
    except Exception:
        pass
    return leaves, values, len(payload) if payload is not None else 0


def _valid_numeric_imas_value(value):
    try:
        values = np.asarray(value, dtype=float)
        return (
            values.size > 0
            and np.all(np.isfinite(values))
            and np.all(np.abs(values) < 1.0e30)
        )
    except Exception:
        return False


def _wave_parent_schema_present(waves):
    try:
        return _valid_numeric_imas_value(waves.vacuum_toroidal_field.b0)
    except Exception:
        return False


def _capture_wave_schema_templates(waves, input_slices, param_process,
                                   config_folder_path):
    if waves is None:
        return
    active = _selected_active_wave_sources(input_slices, param_process)
    if not any(active.values()):
        return
    counters = {"ec": 0, "ic": 0}
    templates = _WAVE_SCHEMA_TEMPLATES.setdefault(
        _wave_template_key(config_folder_path),
        {"base": None, "parent": None, "slots": {}},
    )
    # Allow a process that imported an older in-memory cache layout to recover
    # harmlessly (useful during interactive workflow development).
    if "slots" not in templates:
        templates.clear()
        templates.update({"base": None, "parent": None, "slots": {}})
    templates.setdefault("parent", None)
    try:
        coherent_waves = waves.coherent_wave
    except Exception:
        return

    base_score = _schema_richness(waves)
    current_base = templates.get("base")
    base_is_richer = (
        current_base is None
        or base_score[:2] > current_base["score"][:2]
    )
    parent_candidate = (
        templates.get("parent") is None
        and _wave_parent_schema_present(waves)
    )
    slot_candidates = []
    for wave_index, wave in enumerate(coherent_waves):
        kind = _wave_source_kind(wave)
        if kind not in counters:
            continue
        source_index = counters[kind]
        counters[kind] += 1
        if not active.get(kind, False):
            continue
        slot_key = (kind, source_index)
        score = _schema_richness(wave)
        current = templates["slots"].get(slot_key)
        if current is None or score[:2] > current["score"][:2]:
            slot_candidates.append((slot_key, wave_index, score))

    # Actor schemas normally stabilize after their first populated output.
    # Avoid serializing a potentially large 81-wave IDS at every time slice.
    if not base_is_richer and not parent_candidate and not slot_candidates:
        return
    payload = _serialize_ids_snapshot(waves)
    if payload is None:
        return
    if base_is_richer:
        templates["base"] = {
            "payload": payload,
            "score": (*base_score[:2], len(payload)),
        }
    if parent_candidate:
        templates["parent"] = {"payload": payload}
        print("  [HCD outputs] Cached waves parent schema", flush=True)
    for slot_key, wave_index, score in slot_candidates:
        templates["slots"][slot_key] = {
            "payload": payload,
            "wave_index": wave_index,
            "score": (*score[:2], len(payload)),
        }


def _restore_full_wave_schema_template(output_ids, input_slices, param_process,
                                       timenow, config_folder_path):
    """Restore the richest complete waves schema for a fully inactive slice."""
    if any(_selected_active_wave_sources(
            input_slices, param_process).values()):
        return False
    templates = _WAVE_SCHEMA_TEMPLATES.get(
        _wave_template_key(config_folder_path), {})
    base = templates.get("base") if isinstance(templates, dict) else None
    if base is None:
        return False
    restored = _deserialize_ids_snapshot("waves", base.get("payload"))
    if restored is None:
        return False
    _ensure_ids_time(restored, timenow)
    output_ids["waves"] = restored
    return True


def _restore_wave_parent_schema_template(output_ids, config_folder_path):
    """Restore stable waves-level fields that merge actors may omit."""
    waves = output_ids.get("waves")
    if waves is None:
        return False
    templates = _WAVE_SCHEMA_TEMPLATES.get(
        _wave_template_key(config_folder_path), {})
    parent = templates.get("parent") if isinstance(templates, dict) else None
    if parent is None:
        print("  [HCD outputs] WARNING: waves parent schema is unavailable",
              flush=True)
        return False
    restored = _deserialize_ids_snapshot("waves", parent.get("payload"))
    if restored is None:
        return False

    refreshed = False
    target = waves.vacuum_toroidal_field
    source = restored.vacuum_toroidal_field
    for field_name in ("r0", "b0"):
        try:
            current = getattr(target, field_name)
            template_value = getattr(source, field_name)
            value = (
                template_value
                if _valid_numeric_imas_value(template_value)
                else current
            )
            if _valid_numeric_imas_value(value):
                # Reassignment is deliberate: put_slice only extends this
                # time-dependent dataset when the node is materialized for
                # the current slice, even if a merge result exposes a cached
                # value through has_value.
                _set_array_or_scalar(target, field_name, np.asarray(value))
                refreshed = True
        except Exception:
            pass
    if refreshed:
        try:
            b0 = np.asarray(target.b0, dtype=float)
            print(
                "  [HCD outputs] Materialized waves parent schema "
                f"(b0_shape={b0.shape}, b0={b0.tolist()})",
                flush=True,
            )
        except Exception:
            print("  [HCD outputs] Materialized waves parent schema",
                  flush=True)
    return refreshed


def _restore_wave_schema_template(coherent_waves, slot_index, source_kind,
                                  source_index, config_folder_path,
                                  snapshot_cache=None):
    templates = _WAVE_SCHEMA_TEMPLATES.get(
        _wave_template_key(config_folder_path), {})
    slots = templates.get("slots", {}) if isinstance(templates, dict) else {}
    template = slots.get((source_kind, source_index))
    if template is None:
        return False
    payload = template.get("payload")
    cache_key = id(payload)
    restored = (snapshot_cache.get(cache_key)
                if snapshot_cache is not None else None)
    if restored is None:
        restored = _deserialize_ids_snapshot("waves", payload)
        if restored is not None and snapshot_cache is not None:
            snapshot_cache[cache_key] = restored
    if restored is None:
        return False
    try:
        coherent_waves[slot_index] = restored.coherent_wave[
            template["wave_index"]]
        return True
    except Exception:
        return False


def _capture_core_sources_schema_template(core_sources, input_slices,
                                          param_process, config_folder_path):
    if core_sources is None:
        return
    try:
        if len(core_sources.source) == 0:
            return
    except Exception:
        return
    if not any(_selected_active_wave_sources(
            input_slices, param_process).values()):
        return
    score = _schema_richness(core_sources)
    key = _wave_template_key(config_folder_path)
    current = _CORE_SOURCES_SCHEMA_TEMPLATES.get(key)
    if current is not None and score[:2] <= current["score"][:2]:
        return
    payload = _serialize_ids_snapshot(core_sources)
    if payload is None:
        return
    if current is None or score[:2] > current["score"][:2]:
        _CORE_SOURCES_SCHEMA_TEMPLATES[key] = {
            "payload": payload,
            "score": (*score[:2], len(payload)),
        }


def _restore_core_sources_schema_template(output_ids, timenow,
                                          config_folder_path):
    current = output_ids.get("core_sources")
    try:
        if current is not None and len(current.source) > 0:
            return False
    except Exception:
        pass
    template = _CORE_SOURCES_SCHEMA_TEMPLATES.get(
        _wave_template_key(config_folder_path))
    if template is None:
        return False
    restored = _deserialize_ids_snapshot(
        "core_sources", template.get("payload"))
    if restored is None:
        return False
    _ensure_ids_time(restored, timenow)
    for source in restored.source:
        _zero_existing_core_source_payload(source, timenow)
    output_ids["core_sources"] = restored
    return True


def _align_selected_wave_slots(waves, input_slices, param_process):
    """Keep actor order and add only the independently selected source slots.

    Recognized actor waves retain their relative order.  Missing slots are
    appended in configuration order, while waves belonging to an unselected
    EC/IC branch are removed.  This makes EC-only and IC-only first-class
    configurations instead of treating either branch as a dependency of the
    other.
    """
    selected_counts = _selected_wave_counts(input_slices, param_process)
    if not selected_counts:
        return waves, []
    try:
        current_kinds = [
            _wave_source_kind(wave) for wave in waves.coherent_wave]
    except Exception:
        current_kinds = []

    known_counts = {kind: 0 for kind in selected_counts}
    for kind in current_kinds:
        if (kind in selected_counts
                and known_counts[kind] < selected_counts[kind]):
            known_counts[kind] += 1
    unknown_capacity = {
        kind: selected_counts[kind] - known_counts[kind]
        for kind in selected_counts
    }
    source_indices = {kind: 0 for kind in selected_counts}
    plan = []

    for wave_index, kind in enumerate(current_kinds):
        assigned_kind = None
        if (kind in selected_counts
                and source_indices[kind] < selected_counts[kind]):
            assigned_kind = kind
        elif kind is None:
            assigned_kind = next(
                (candidate for candidate in selected_counts
                 if unknown_capacity[candidate] > 0),
                None,
            )
            if assigned_kind is not None:
                unknown_capacity[assigned_kind] -= 1
        if assigned_kind is None:
            continue
        source_index = source_indices[assigned_kind]
        source_indices[assigned_kind] += 1
        plan.append((assigned_kind, source_index, wave_index))

    for kind, count in selected_counts.items():
        while source_indices[kind] < count:
            source_index = source_indices[kind]
            source_indices[kind] += 1
            plan.append((kind, source_index, None))

    retained_indices = [wave_index for _, _, wave_index in plan
                        if wave_index is not None]
    identity_layout = (
        retained_indices == list(range(len(current_kinds)))
        and len(plan) == len(current_kinds)
    )
    if not identity_layout:
        payload = _serialize_ids_snapshot(waves)
        restored = _deserialize_ids_snapshot("waves", payload)
        try:
            waves.coherent_wave.resize(0)
            waves.coherent_wave.resize(len(plan))
            if restored is not None:
                for slot_index, (_, _, wave_index) in enumerate(plan):
                    if wave_index is not None:
                        waves.coherent_wave[slot_index] = \
                            restored.coherent_wave[wave_index]
        except Exception:
            pass
    return waves, [(kind, source_index) for kind, source_index, _ in plan]


def _ensure_waves_placeholders(input_slices, output_ids, param_process, timenow,
                               config_folder_path=None):
    if not _selected_wave_counts(input_slices, param_process):
        return

    waves = _ensure_output_slice(output_ids, "waves", timenow)
    waves, slots = _align_selected_wave_slots(
        waves, input_slices, param_process)
    output_ids["waves"] = waves

    active_sources = _selected_active_wave_sources(
        input_slices, param_process)
    snapshot_cache = {}

    for slot_index, (source_kind, source_index) in enumerate(slots):
        slot_was_missing = (
            _wave_source_kind(waves.coherent_wave[slot_index]) != source_kind
        )
        source_is_inactive = not active_sources.get(source_kind, False)
        if not slot_was_missing and not source_is_inactive:
            continue
        if slot_was_missing or source_is_inactive:
            _restore_wave_schema_template(
                waves.coherent_wave,
                slot_index,
                source_kind,
                source_index,
                config_folder_path,
                snapshot_cache=snapshot_cache,
            )
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


def _retain_selected_hcd_sources(core_sources, selected_names):
    """Drop unselected H&CD sources while preserving actor order."""
    try:
        current_names = [_source_name(source) for source in core_sources.source]
    except Exception:
        return
    retained_indices = [
        index for index, name in enumerate(current_names)
        if name not in {"ec", "ic", "nbi"} or name in selected_names
    ]
    if retained_indices == list(range(len(current_names))):
        return

    payload = _serialize_ids_snapshot(core_sources)
    restored = _deserialize_ids_snapshot("core_sources", payload)
    if restored is None:
        return
    try:
        core_sources.source.resize(0)
        core_sources.source.resize(len(retained_indices))
        for index, source_index in enumerate(retained_indices):
            core_sources.source[index] = restored.source[source_index]
    except Exception:
        return


def _code_field_name(code_obj):
    try:
        name = str(code_obj.name).strip().lower()
        if name:
            return name
    except Exception:
        pass
    return ""


def _code_field_index(code_obj):
    try:
        return int(code_obj.index)
    except Exception:
        return None


def _wave_is_ic(coherent_wave):
    """Best-effort guard to keep EC fallback from absorbing IC waves."""
    try:
        type_name = _code_field_name(coherent_wave.identifier.type)
        type_index = _code_field_index(coherent_wave.identifier.type)
        solver_name = _code_field_name(coherent_wave.wave_solver_type)
    except Exception:
        return False

    if "ic" in type_name or type_index == 3 or "ic" in solver_name:
        return True
    return False


def waves_summary_mw(waves):
    if waves is None:
        return 0, 0.0
    count = 0
    power = 0.0
    try:
        count = _safe_len(waves.coherent_wave)
        for wave in waves.coherent_wave:
            if _safe_len(wave.global_quantities) > 0:
                value = float(wave.global_quantities[0].power)
                if np.isfinite(value) and abs(value) < 1.0e30:
                    power += value
    except Exception:
        pass
    return count, power * 1.0e-6


def core_source_has_electron_heating_signal(core_sources, source_name="ec"):
    if core_sources is None:
        return False
    try:
        for source in core_sources.source:
            if _source_name(source) != source_name:
                continue
            for profile in source.profiles_1d:
                energy = np.asarray(profile.electrons.energy, dtype=float)
                finite = energy[
                    np.isfinite(energy) & (np.abs(energy) < 1.0e30)]
                if finite.size > 0 and np.any(np.abs(finite) > 0.0):
                    return True
    except Exception:
        return False
    return False


def _ec_profiles_from_waves(waves):
    if waves is None or _safe_len(waves.coherent_wave) == 0:
        return None

    target_grid = None
    total_power_density = None
    total_current_parallel = None
    ec_power_w = 0.0

    for coherent_wave in waves.coherent_wave:
        if _wave_is_ic(coherent_wave) or _safe_len(coherent_wave.profiles_1d) == 0:
            continue
        try:
            if _safe_len(coherent_wave.global_quantities) > 0:
                value = float(coherent_wave.global_quantities[0].power)
                if np.isfinite(value) and abs(value) < 1.0e30:
                    ec_power_w += value
        except Exception:
            pass
        profile = coherent_wave.profiles_1d[0]
        rho = _valid_profile_array(profile.grid.rho_tor_norm)
        if rho is None:
            continue
        power_density = _valid_profile_array(profile.power_density, expected_size=rho.size)
        current_parallel = _valid_profile_array(
            profile.current_parallel_density,
            expected_size=rho.size,
        )
        if power_density is None and current_parallel is None:
            continue
        if target_grid is None:
            target_grid = rho
        total_power_density = _add_profile_to_grid(
            total_power_density, rho, power_density, target_grid)
        total_current_parallel = _add_profile_to_grid(
            total_current_parallel, rho, current_parallel, target_grid)

    if target_grid is None or total_power_density is None:
        return None

    if total_current_parallel is None:
        total_current_parallel = np.zeros_like(total_power_density)

    return target_grid, total_power_density, total_current_parallel, ec_power_w * 1.0e-6


def _ensure_ids_time(ids_data, timenow):
    try:
        ids_data.ids_properties.homogeneous_time = 1
    except Exception:
        pass
    if timenow is None or not hasattr(ids_data, "time"):
        return
    try:
        ids_data.time = np.asarray([float(timenow)], dtype=float)
    except Exception:
        try:
            ids_data.time.resize(1)
            ids_data.time[0] = float(timenow)
        except Exception:
            pass


def _find_or_append_source(core_sources, source_name):
    blank_index = None
    try:
        for idx, source in enumerate(core_sources.source):
            name = _source_name(source)
            if name == source_name:
                return source
            if not name and blank_index is None:
                blank_index = idx
    except Exception:
        pass

    try:
        if blank_index is None:
            blank_index = _safe_len(core_sources.source)
            core_sources.source.resize(blank_index + 1, keep=True)
        return core_sources.source[blank_index]
    except Exception:
        return None


def repair_ec_core_sources_from_waves(output_ids, timenow=None):
    """Fill only the EC source from waves when hcd2core_sources returns empty EC.

    This is an internal compatibility guard for DD4 H&CD coupling. It preserves
    any existing non-EC sources instead of replacing the complete IDS.
    """
    waves = output_ids.get("waves") if output_ids else None
    n_waves, p_waves_mw = waves_summary_mw(waves)
    if n_waves == 0 or p_waves_mw <= 1.0e-9:
        return False

    core_sources = output_ids.get("core_sources")
    if core_source_has_electron_heating_signal(core_sources, "ec"):
        return False

    profiles = _ec_profiles_from_waves(waves)
    if profiles is None:
        return False
    rho, power_density, current_parallel, ec_power_mw = profiles

    if _ids_needs_placeholder(core_sources):
        core_sources = _create_ids("core_sources")
        output_ids["core_sources"] = core_sources
    _ensure_ids_time(core_sources, timenow)

    source = _find_or_append_source(core_sources, "ec")
    if source is None:
        return False

    source.identifier.name = "ec"
    source.identifier.index = 3
    _ensure_source_global_quantities(source, timenow)
    try:
        source.global_quantities[0].power = float(ec_power_mw) * 1.0e6
        source.global_quantities[0].electrons.power = float(ec_power_mw) * 1.0e6
    except Exception:
        pass

    try:
        if _safe_len(source.profiles_1d) == 0:
            source.profiles_1d.resize(1)
        profile = source.profiles_1d[0]
    except Exception:
        return False

    try:
        profile.time = float(timenow) if timenow is not None else profile.time
    except Exception:
        pass

    zeros = np.zeros_like(rho, dtype=float)
    profile.grid.rho_tor_norm = rho
    _set_if_missing(profile.grid, "rho_tor", rho.copy())
    _set_if_missing(profile.grid, "rho_pol_norm", rho.copy())
    _set_if_missing(profile.grid, "psi", zeros.copy())
    _set_if_missing(profile.grid, "area", zeros.copy())
    _set_if_missing(profile.grid, "surface", zeros.copy())
    _set_if_missing(profile.grid, "volume", zeros.copy())
    profile.electrons.energy = power_density
    profile.j_parallel = current_parallel
    return True


def _iter_nonempty_ids_leaves(node):
    """Recursively yield assigned IMAS leaf nodes without schema internals."""
    if node is None:
        return
    if type(node).__name__ == "IDSStructArray":
        for item in node:
            yield from _iter_nonempty_ids_leaves(item)
        return
    iterator = getattr(node, "iter_nonempty_", None)
    if callable(iterator):
        for child in iterator():
            yield from _iter_nonempty_ids_leaves(child)
        return
    yield node


def sanitize_hcd_output_numerics(output_ids):
    """Replace non-finite values and IMAS sentinels in assigned output leaves.

    Real physics actors occasionally assign NaN to auxiliary DD fields (for
    example Torbeam's per-beam ``grid.area`` outside its interpolation range).
    Once assigned, those values are persisted by HDF5 and can poison later
    readers even though the primary deposition profile is valid.  Sanitize all
    generated HCD IDS objects at the shared Legacy/Hybrid/Pure write boundary.
    """
    if not isinstance(output_ids, dict):
        return 0

    replacements = 0
    for ids_obj in output_ids.values():
        for leaf in _iter_nonempty_ids_leaves(ids_obj):
            try:
                values = np.asarray(leaf.value)
            except Exception:
                continue
            if values.dtype.kind in "fc":
                invalid = ~np.isfinite(values) | (np.abs(values) >= 1.0e30)
            elif values.dtype.kind in "iu":
                invalid = values == -999_999_999
            else:
                continue
            if not np.any(invalid):
                continue

            cleaned = values.copy()
            cleaned[invalid] = 0
            try:
                leaf.value = cleaned.item() if cleaned.ndim == 0 else cleaned
            except Exception:
                continue
            replacements += int(np.count_nonzero(invalid))
    return replacements


def _clean_numeric_field(parent, field_name):
    try:
        values = np.asarray(getattr(parent, field_name))
    except Exception:
        return 0
    if values.dtype.kind in "fc":
        invalid = ~np.isfinite(values) | (np.abs(values) >= 1.0e30)
    elif values.dtype.kind in "iu":
        invalid = values == -999_999_999
    else:
        return 0
    if not np.any(invalid):
        return 0

    cleaned = values.copy()
    cleaned[invalid] = 0
    try:
        setattr(
            parent,
            field_name,
            cleaned.item() if cleaned.ndim == 0 else cleaned,
        )
    except Exception:
        return 0
    return int(np.count_nonzero(invalid))


def sanitize_core_sources_numerics(core_sources):
    """Apply the finite-value contract to known H&CD source fields."""
    if core_sources is None:
        return 0

    replacements = 0
    physical_fields = (
        "power", "current_parallel", "total_ion_power", "j_parallel",
        "energy", "particles", "momentum_phi", "momentum_tor",
        "torque_phi", "torque_tor", "total_ion_energy",
    )
    try:
        sources = core_sources.source
    except Exception:
        sources = ()

    for source in sources:
        for quantities in getattr(source, "global_quantities", []):
            for field_name in physical_fields:
                replacements += _clean_numeric_field(quantities, field_name)
            try:
                for field_name in physical_fields:
                    replacements += _clean_numeric_field(
                        quantities.electrons, field_name)
            except Exception:
                pass
            for ion in getattr(quantities, "ion", []):
                for field_name in physical_fields:
                    replacements += _clean_numeric_field(ion, field_name)

        for profile in getattr(source, "profiles_1d", []):
            for field_name in physical_fields:
                replacements += _clean_numeric_field(profile, field_name)
            try:
                for field_name in physical_fields:
                    replacements += _clean_numeric_field(
                        profile.electrons, field_name)
            except Exception:
                pass
            for ion in getattr(profile, "ion", []):
                for field_name in physical_fields:
                    replacements += _clean_numeric_field(ion, field_name)

    replacements += sanitize_hcd_output_numerics(
        {"core_sources": core_sources})
    return replacements


# Compatibility for existing callers; no TORAX-specific reshaping is applied.
sanitize_core_sources_for_torax = sanitize_core_sources_numerics


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
    """Ensure profiles_1d[0] has the stable DD4 source schema.

    This is used for both EC and IC placeholders.  Without it, a later inactive
    slice can shrink an actor-established 1D grid to zero; HDF5 then either
    becomes unreadable or exposes different source shapes across the pulse.

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
    elif source_kind == "nbi":
        source.identifier.name = "nbi"
        source.identifier.index = 2
        try:
            source.identifier.description = \
                "Source from Neutral Beam Injection"
        except Exception:
            pass
    _ensure_source_global_quantities(source, timenow)
    if source_kind in {"ec", "ic"} and input_slices is not None:
        _ensure_source_profiles_1d(
            source, sibling_sources, input_slices, timenow, config_folder_path)


def _zero_existing_core_source_payload(source, timenow):
    """Zero source/sink terms while retaining the actor-established schema."""
    physical_fields = (
        "power", "current_parallel", "total_ion_power", "j_parallel",
        "energy", "particles", "momentum_phi", "momentum_tor",
        "torque_phi", "torque_tor", "total_ion_energy",
    )
    for quantities in getattr(source, "global_quantities", []):
        try:
            quantities.time = timenow
        except Exception:
            pass
        for field_name in physical_fields:
            _zero_field_like(quantities, field_name)
        try:
            for field_name in physical_fields:
                _zero_field_like(quantities.electrons, field_name)
        except Exception:
            pass
        for ion in getattr(quantities, "ion", []):
            for field_name in physical_fields:
                _zero_field_like(ion, field_name)

    for profile in getattr(source, "profiles_1d", []):
        try:
            profile.time = timenow
        except Exception:
            pass
        for field_name in physical_fields:
            _zero_field_like(profile, field_name)
        try:
            for field_name in physical_fields:
                _zero_field_like(profile.electrons, field_name)
        except Exception:
            pass
        for ion in getattr(profile, "ion", []):
            for field_name in physical_fields:
                _zero_field_like(ion, field_name)


def _expected_source_names(param_process):
    process_kinds = {
        "ec_wave_solver": "ec",
        "ic_wave_solver": "ic",
        "nbi_source": "nbi",
        "nbi_fp": "nbi",
    }
    expected = []
    try:
        process_names = list(param_process)
    except Exception:
        process_names = []
    for process_name in process_names:
        source_name = process_kinds.get(str(process_name))
        if (source_name is not None
                and source_name not in expected
                and _process_is_selected(param_process, process_name)):
            expected.append(source_name)
    if not process_names:
        for process_name, source_name in process_kinds.items():
            if (_process_is_selected(param_process, process_name)
                    and source_name not in expected):
                expected.append(source_name)
    return expected


def _ensure_core_sources_placeholders(input_slices, output_ids, param_process,
                                      timenow, config_folder_path=None):
    if not _process_is_selected(param_process, "fill_core_sources"):
        return

    expected = _expected_source_names(param_process)
    if not expected:
        return

    core_sources = _ensure_output_slice(output_ids, "core_sources", timenow)
    _retain_selected_hcd_sources(core_sources, set(expected))
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

    active_sources = _selected_active_wave_sources(
        input_slices, param_process)
    for source, name in zip(core_sources.source, names):
        _ensure_source_global_quantities(source, timenow)
        if name in {"ec", "ic"}:
            if not active_sources.get(name, False):
                _zero_existing_core_source_payload(source, timenow)
            _ensure_source_profiles_1d(
                source, core_sources.source, input_slices, timenow,
                config_folder_path)


def stabilize_selected_hcd_outputs(input_slices, output_ids, param_process,
                                    timenow, config_folder_path=None):
    """Repair and stabilize selected H&CD outputs before database storage.

    Keeping this at the shared write boundary gives legacy, Hybrid M3, and
    Pure M3 the same DD4 contract.  The Hybrid executor also performs the
    repair immediately after hcd2core_sources so downstream in-process users
    see it early; all helpers here are deliberately idempotent.
    """
    if param_process is None or timenow is None:
        return
    _capture_wave_schema_templates(
        output_ids.get("waves"), input_slices, param_process,
        config_folder_path)
    _capture_core_sources_schema_template(
        output_ids.get("core_sources"), input_slices, param_process,
        config_folder_path)
    _restore_full_wave_schema_template(
        output_ids, input_slices, param_process, timenow,
        config_folder_path)
    _restore_wave_parent_schema_template(output_ids, config_folder_path)
    _ensure_waves_placeholders(
        input_slices, output_ids, param_process, timenow,
        config_folder_path=config_folder_path,
    )
    _restore_core_sources_schema_template(
        output_ids, timenow, config_folder_path)
    stabilization_disabled = os.environ.get(
        "HCDWF_DISABLE_CORE_SOURCE_STABILIZATION", ""
    ).lower() in {"1", "true", "yes", "on"}
    if not stabilization_disabled:
        repair_ec_core_sources_from_waves(output_ids, timenow=timenow)
    _ensure_core_sources_placeholders(
        input_slices, output_ids, param_process, timenow,
        config_folder_path=config_folder_path,
    )
    sanitized = sanitize_core_sources_numerics(
        output_ids.get("core_sources"))
    sanitized += sanitize_hcd_output_numerics(output_ids)
    if sanitized:
        print(
            f"  [HCD outputs] Replaced {sanitized} non-finite/sentinel values",
            flush=True,
        )
