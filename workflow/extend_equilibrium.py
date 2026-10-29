#!/usr/bin/env python
"""
Extend a fixed-boundary equilibrium IDS (e.g. JETTO/ESCO output) outside the
separatrix, so that HCD ray/beam-tracing actors (GRAY, TORBEAM, ...) see a
smooth psi and B field from the launcher to the plasma.

Author: J. Lombardo (ITER), October 2026. Data Dictionary 4 (COCOS 17) version
for the TORBEAM DD4 test tree (names and psi sign convention from dd_compat.py).

What it does, per time slice:
  0. Normalises the input field names of profiles_2d[0]: b_field_phi is taken from b_field_tor
     (DD 3 name, present with b_field_phi in DD 3.42, absent in DD 4) when b_field_phi is empty;
     the obsolete DD 3 fields b_r / b_z / b_tor are moved to b_field_r / b_field_z / b_field_phi
     when those are empty, and then emptied.
  1. Extends the rectangular profiles_2d grid with the SAME spacing, so the
     original nodes (and their psi values) are kept unchanged, until the
     requested R,Z box (default: covers the ITER EL and UL launch points).
  2. Keeps psi where psi_N < 1 - CLAMP_TOL on the original grid. Elsewhere (the
     region where the fixed-boundary code clamps psi to psi_boundary, and the
     new nodes) psi_N is extrapolated in the normalised minor radius
     dx = |X - X_axis| / r_boundary(theta) (dx = 1 on the LCFS):
       mode matched: psi_N = 1 + G(theta) ln(dx), G = dx dpsi_N/ddx at the LCFS
                     fitted on the last closed surfaces (0.8 < psi_N < 0.999)
                     -> B_pol approximately continuous across the LCFS.
     The CLI also accepts --mode none (slices copied without extension: A/B
     reference on exactly the same time slices).
  3. Recomputes b_field_r, b_field_z from psi and b_field_phi = F(psi)/R,
     with F = F_boundary outside the plasma; phi (toroidal flux) is
     extrapolated linearly in psi_N. When b_field_tor was filled on input it receives the
     same extended field as b_field_phi.
     theta (when filled) is recomputed on the extended grid with the convention of
     THETA_CONVENTIONS that reproduces the stored theta inside the LCFS to THETA_TOL; when none
     does, the stored values are kept on the original nodes inside the LCFS and the other
     nodes get the closest convention (reported in the returned info).
     COCOS 17 (DD4): B_R = -(dpsi/dZ)/(2 pi R), B_Z = (dpsi/dR)/(2 pi R),
     written below with dd_compat.COCOS_PSI (= +1 in the DD4 tree).
  4. (CLI) Writes equilibrium (selected slices) + core_profiles (copied) to a
     new IMAS entry, to be used as scenario_uri_link of the HCD actors.

This is NOT a reconstructed (free-boundary) equilibrium: outside the
separatrix psi is extrapolated without any coil current, which is good enough
for the HCD actors to trace the beams and nothing else. The caveat is appended
to ids_properties.comment of the extended IDS.

Library use (in-memory IMAS-Python equilibrium, DD 4):
  from extend_equilibrium import extend_equilibrium_ids, extend_slice
  infos = extend_equilibrium_ids(eq, box=DEFAULT_BOX, source=uri)  # all time slices + comment
  info, diag = extend_slice(eq.time_slice[0], box)                 # one time slice, in place

Usage (IMAS-Python environment of the DD4 tree, e.g. source config_sdcc.sh):
  python extend_equilibrium.py -i <input_uri> -o <output_uri> \
         [--times 10:95:5] [--mode matched|none] [--box 3.9,10.6,-4.6,4.9] \
         [--plot <dir>] [--launchers <uri with ec_launchers>]
Input data in another DD version are converted to IMAS_VERSION at read time.
"""

import argparse
import os

import numpy as np
import imas
from scipy.interpolate import CubicSpline

from workflow import dd_compat as dd

TWOPI = 2.0 * np.pi
# |psi_N - 1| below which psi counts as clamped to psi_boundary. The clamped value of
# JETTO/ESCO outputs is not exactly psi_boundary (|psi_N - 1| up to ~5e-6 seen in SRO case 4.1)
CLAMP_TOL = 1e-4
# Rmin, Rmax, Zmin, Zmax [m] covered by the extended grid: ITER EC equatorial and upper launchers
DEFAULT_BOX = (3.9, 10.6, -4.6, 4.9)
MODES = ("matched",)
# Obsolete DD 3 profiles_2d fields and the field that replaces them (none of them exists in DD 4)
OBSOLETE_2D = (("b_r", "b_field_r"), ("b_z", "b_field_z"), ("b_tor", dd.B_FIELD_PHI))
# Candidate definitions of profiles_2d/theta [rad] on the (R, Z) nodes, axis at (r0, z0)
THETA_CONVENTIONS = {
    "-atan2(Z-Z_axis, R-R_axis) in [0, 2pi)": lambda R, Z, r0, z0: np.mod(-np.arctan2(Z - z0, R - r0), TWOPI),
    "-atan2(Z-Z_axis, R-R_axis) in (-pi, pi]": lambda R, Z, r0, z0: -np.arctan2(Z - z0, R - r0),
    "atan2(Z-Z_axis, R-R_axis) in [0, 2pi)": lambda R, Z, r0, z0: np.mod(np.arctan2(Z - z0, R - r0), TWOPI),
    "atan2(Z-Z_axis, R-R_axis) in (-pi, pi]": lambda R, Z, r0, z0: np.arctan2(Z - z0, R - r0),
    "-atan2(Z, R) in [0, 2pi)": lambda R, Z, r0, z0: np.mod(-np.arctan2(Z, R), TWOPI),
    "-atan2(Z, R) in (-pi, pi]": lambda R, Z, r0, z0: -np.arctan2(Z, R),
    "atan2(Z, R) in [0, 2pi)": lambda R, Z, r0, z0: np.mod(np.arctan2(Z, R), TWOPI),
    "atan2(Z, R) in (-pi, pi]": lambda R, Z, r0, z0: np.arctan2(Z, R),
}
# max |theta_stored - theta_convention| [rad] inside the LCFS for a convention to count as matching
THETA_TOL = 1e-10
CAVEAT = (
    "psi extended outside the separatrix for HCD actors (extend_equilibrium.py, mode={mode}); "
    "NOT a reconstructed equilibrium outside the LCFS. Source: {source}"
)


def parse_times(spec, native):
    """'10:95:5' -> nearest native slice to each requested time (unique)."""
    if ":" in spec:
        t0, t1, dt = (float(x) for x in spec.split(":"))
        req = np.arange(t0, t1 + 0.5 * dt, dt)
    else:
        req = np.array([float(x) for x in spec.split(",")])
    idx = sorted({int(np.argmin(np.abs(native - t))) for t in req})
    return native[idx]


def extend_axis(x, xmin, xmax):
    """Append nodes with the original spacing until [xmin, xmax] is covered."""
    dx = (x[-1] - x[0]) / (len(x) - 1)
    nlo = max(int(np.ceil((x[0] - xmin) / dx)), 0)
    nhi = max(int(np.ceil((xmax - x[-1]) / dx)), 0)
    lo = x[0] - dx * np.arange(nlo, 0, -1)
    hi = x[-1] + dx * np.arange(1, nhi + 1)
    return np.concatenate([lo, x, hi]), nlo


def boundary_radius(ts, r0, z0):
    """Periodic spline r_b(theta) of the LCFS seen from the magnetic axis."""
    rb = np.array(ts.boundary.outline.r, dtype=float)
    zb = np.array(ts.boundary.outline.z, dtype=float)
    theta = np.arctan2(zb - z0, rb - r0)
    rad = np.hypot(rb - r0, zb - z0)
    theta, keep = np.unique(theta, return_index=True)
    rad = rad[keep]
    theta = np.append(theta, theta[0] + TWOPI)
    rad = np.append(rad, rad[0])
    spl = CubicSpline(theta, rad, bc_type="periodic")
    return lambda th: spl(np.mod(th - theta[0], TWOPI) + theta[0])


def fit_gradient(dx, theta, psin, nbins=16):
    """G(theta) such that psi_N ~ 1 + G ln(dx) on the last closed surfaces."""
    sel = (psin > 0.8) & (psin < 0.999) & (dx > 0.5) & (dx < 0.9995)
    g_pts = (psin[sel] - 1.0) / np.log(dx[sel])
    g_all = np.median(g_pts) if g_pts.size else 2.0
    edges = np.linspace(-np.pi, np.pi, nbins + 1)
    centres = 0.5 * (edges[1:] + edges[:-1])
    g = np.full(nbins, g_all)
    for k in range(nbins):
        m = (theta[sel] >= edges[k]) & (theta[sel] < edges[k + 1])
        if m.sum() >= 3:
            g[k] = np.median(g_pts[m])
    # mild periodic smoothing, then periodic interpolation
    g = 0.25 * np.roll(g, 1) + 0.5 * g + 0.25 * np.roll(g, -1)
    th = np.append(centres, centres[0] + TWOPI)
    spl = CubicSpline(th, np.append(g, g[0]), bc_type="periodic")
    return (lambda t: spl(np.mod(t - centres[0], TWOPI) + centres[0])), g_all


def normalise_fields(p2):
    """Normalise the toroidal-field and obsolete DD 3 names of profiles_2d p2 in place:
    b_field_phi from b_field_tor when b_field_phi is empty; b_r / b_z / b_tor moved to
    b_field_r / b_field_z / b_field_phi when those are empty, then emptied.
    Returns True when b_field_tor is filled on input."""
    tor_in = hasattr(p2, "b_field_tor") and p2.b_field_tor.has_value
    if tor_in and not getattr(p2, dd.B_FIELD_PHI).has_value:
        setattr(p2, dd.B_FIELD_PHI, np.array(p2.b_field_tor, dtype=float))
    for old, twin in OBSOLETE_2D:
        if hasattr(p2, old) and getattr(p2, old).has_value:
            if not getattr(p2, twin).has_value:
                setattr(p2, twin, np.array(getattr(p2, old), dtype=float))
            setattr(p2, old, np.empty((0, 0)))
    return tor_in


def extend_theta(theta_old, R, Z, r0, z0, sl, inside_old):
    """theta on the extended grid (R, Z); sl = original nodes, inside_old = original nodes inside
    the LCFS. Returns (theta, convention name, max |stored - convention| inside, matched)."""
    dev = {}
    for name, conv in THETA_CONVENTIONS.items():
        d = theta_old - conv(R[sl], Z[sl], r0, z0)
        dev[name] = (
            float(np.max(np.abs(d[inside_old]))),
            float(np.median(np.abs(np.angle(np.exp(1j * d[inside_old]))))),
        )
    best = min(dev, key=lambda k: dev[k][0])
    if dev[best][0] <= THETA_TOL:
        return THETA_CONVENTIONS[best](R, Z, r0, z0), best, dev[best][0], True
    best = min(dev, key=lambda k: dev[k][1])
    theta = THETA_CONVENTIONS[best](R, Z, r0, z0)
    theta[sl][inside_old] = theta_old[inside_old]
    return theta, best, dev[best][0], False


def extend_slice(ts, box=DEFAULT_BOX, mode="matched"):
    """Extend profiles_2d[0] of the equilibrium time slice ts in place (grid, psi, phi,
    b_field_r/z/phi, b_field_tor and theta when filled, r, z), after normalise_fields. Needs
    boundary.outline, global_quantities (magnetic axis, psi on axis), the boundary psi
    (dd_compat.psi_boundary), profiles_1d psi/f and the stored b_field_r and b_field_phi (used for
    the sign check in the core). Returns (info, diag): info = dict of diagnostics, diag = (r_old,
    z_old, psin_old, r_new, z_new, psin) for plot_slice."""
    if mode not in MODES:
        raise ValueError(f"extend_slice: mode {mode!r} not in {MODES}")
    p2 = ts.profiles_2d[0]
    tor_in = normalise_fields(p2)
    gq = ts.global_quantities
    psi_ax = float(getattr(gq, dd.PSI_MAGNETIC_AXIS))
    psi_b = float(dd.psi_boundary(ts))
    r0, z0 = float(gq.magnetic_axis.r), float(gq.magnetic_axis.z)

    r_old = np.array(p2.grid.dim1, dtype=float)
    z_old = np.array(p2.grid.dim2, dtype=float)
    psi_old = np.array(p2.psi, dtype=float)
    br_old = np.array(p2.b_field_r, dtype=float)
    bt_old = np.array(getattr(p2, dd.B_FIELD_PHI), dtype=float)

    r_new, i0 = extend_axis(r_old, box[0], box[1])
    z_new, j0 = extend_axis(z_old, box[2], box[3])
    R, Z = np.meshgrid(r_new, z_new, indexing="ij")

    psin_old = (psi_old - psi_ax) / (psi_b - psi_ax)
    inside_old = np.isfinite(psin_old) & (psin_old < 1.0 - CLAMP_TOL)

    rb = boundary_radius(ts, r0, z0)
    theta = np.arctan2(Z - z0, R - r0)
    dx = np.hypot(R - r0, Z - z0) / rb(theta)

    sl = (slice(i0, i0 + len(r_old)), slice(j0, j0 + len(z_old)))
    gfun, g_all = fit_gradient(dx[sl][inside_old], theta[sl][inside_old], psin_old[inside_old])
    psin_out = 1.0 + gfun(theta) * np.log(np.maximum(dx, 1.0))
    psin_out = np.maximum(psin_out, 1.0)

    psin = psin_out.copy()
    psin[sl][inside_old] = psin_old[inside_old]
    psi = psi_ax + psin * (psi_b - psi_ax)
    psi[sl][inside_old] = psi_old[inside_old]  # bit-exact inside

    # B_pol from psi, COCOS 17 (DD4, COCOS_PSI = +1): B_R = -dpsi/dZ /(2 pi R), B_Z = dpsi/dR /(2 pi R)
    dpsi_dr, dpsi_dz = np.gradient(psi, r_new, z_new, edge_order=2)
    br = -dd.COCOS_PSI * dpsi_dz / (TWOPI * R)
    bz = dd.COCOS_PSI * dpsi_dr / (TWOPI * R)
    # sign/scale check against the stored field where it is trustworthy
    core = inside_old & (psin_old < 0.9)
    ratio = np.median(br[sl][core] / br_old[core]) if core.any() else 1.0
    if ratio < 0:
        br, bz = -br, -bz
        ratio = -ratio

    # B_phi = F(psi)/R, F clamped to F_boundary outside
    psin_1d = (np.array(ts.profiles_1d.psi, dtype=float) - psi_ax) / (psi_b - psi_ax)
    f_1d = np.array(ts.profiles_1d.f, dtype=float)
    order = np.argsort(psin_1d)
    bt = np.interp(psin, psin_1d[order], f_1d[order]) / R
    if np.median(bt[sl][core] / bt_old[core]) < 0:
        bt = -bt

    # toroidal flux: original inside, linear in psi_N (edge slope of phi(psi_N)) outside
    phi_new = None
    if p2.phi.has_value and ts.profiles_1d.phi.has_value:
        phi_1d = np.array(ts.profiles_1d.phi, dtype=float)[order]
        x1d = psin_1d[order]
        slope = (phi_1d[-1] - phi_1d[-2]) / (x1d[-1] - x1d[-2])
        phi_new = np.where(psin <= x1d[-1], np.interp(psin, x1d, phi_1d), phi_1d[-1] + slope * (psin - x1d[-1]))
        phi_new[sl][inside_old] = np.array(p2.phi, dtype=float)[inside_old]

    theta_info = {}
    if p2.theta.has_value:
        theta_new, conv, dev, matched = extend_theta(np.array(p2.theta, dtype=float), R, Z, r0, z0, sl, inside_old)
        theta_info = {"theta_convention": conv, "theta_max_dev_inside": dev, "theta_matched": matched}

    p2.grid.dim1 = r_new
    p2.grid.dim2 = z_new
    p2.psi = psi
    fields = {"r": R, "z": Z, "phi": phi_new, "b_field_r": br, "b_field_z": bz, dd.B_FIELD_PHI: bt}
    if tor_in:
        fields["b_field_tor"] = bt
    if theta_info:
        fields["theta"] = theta_new
    for name, value in fields.items():
        if value is None:
            setattr(p2, name, np.empty((0, 0)))
        elif getattr(p2, name).has_value or name.startswith("b_field"):
            setattr(p2, name, value)
    for c in p2.iter_nonempty_():
        if getattr(c, "shape", None) == psi_old.shape and c.metadata.name not in fields:
            raise RuntimeError(f"profiles_2d/{c.metadata.name} not handled by the extension")

    info = dict(
        t=float(ts.time) if ts.time.has_value else float("nan"),
        grid_old=psi_old.shape,
        grid_new=psi.shape,
        frac_clamped=float(1.0 - inside_old.mean()),
        G=float(g_all),
        br_ratio_core=float(ratio),
        max_dpsi_inside=float(np.max(np.abs(psi[sl][inside_old] - psi_old[inside_old]))),
        bpol_out_max=float(np.max(np.hypot(br, bz)[psin > 1.0])) if (psin > 1.0).any() else 0.0,
    )
    info.update(theta_info)
    return info, (r_old, z_old, psin_old, r_new, z_new, psin)


def append_caveat(eq, mode="matched", source=""):
    """Append the extension caveat to eq.ids_properties.comment (existing text kept)."""
    eq.ids_properties.comment = f"{eq.ids_properties.comment} | " + CAVEAT.format(mode=mode, source=source)


def extend_equilibrium_ids(eq, box=DEFAULT_BOX, mode="matched", source=""):
    """Extend every time slice of the equilibrium IDS eq in place (extend_slice) and append the
    caveat to ids_properties.comment. Returns the list of info dicts, one per time slice."""
    infos = []
    for k, ts in enumerate(eq.time_slice):
        info, _ = extend_slice(ts, box, mode)
        if not np.isfinite(info["t"]) and len(eq.time) > k:
            info["t"] = float(eq.time[k])
        infos.append(info)
    append_caveat(eq, mode, source)
    return infos


def format_info(info):
    text = (
        "t={t:6.2f}s grid {grid_old}->{grid_new} clamped={frac_clamped:.2f} "
        "G={G:.2f} Br_ratio={br_ratio_core:.3f} max|dpsi|_in={max_dpsi_inside:.1e} "
        "Bpol_out_max={bpol_out_max:.2f}T".format(**info)
    )
    if "theta_convention" in info:
        text += " theta: {theta_convention}, max|dtheta|_in={theta_max_dev_inside:.1e}{0}".format(
            "" if info["theta_matched"] else " (NO MATCH: stored theta kept inside the LCFS)", **info
        )
    return text


def plot_slice(diag, info, launch_rz, outdir, mode):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    r_old, z_old, psin_old, r_new, z_new, psin = diag
    fig, ax = plt.subplots(1, 2, figsize=(10, 6), sharey=True)
    levels = np.arange(0.1, 3.01, 0.1)
    for a, (r, z, p, title) in zip(
        ax, [(r_old, z_old, psin_old, "original"), (r_new, z_new, psin, f"extended ({mode})")]
    ):
        a.contour(r, z, p.T, levels=levels, linewidths=0.6)
        a.contour(r, z, p.T, levels=[1.0], colors="k", linewidths=1.5)
        a.add_patch(
            plt.Rectangle(
                (r_old[0], z_old[0]), r_old[-1] - r_old[0], z_old[-1] - z_old[0], fill=False, ls="--", ec="grey"
            )
        )
        if launch_rz is not None:
            a.plot(launch_rz[0], launch_rz[1], "r^", ms=4, label="launch points")
        a.set_aspect("equal")
        a.set_xlabel("R [m]")
        a.set_title(f"{title}, t = {info['t']:.2f} s")
    ax[0].set_ylabel("Z [m]")
    ax[0].legend(loc="lower left")
    fig.tight_layout()
    fn = os.path.join(outdir, f"eqext_{mode}_t{info['t']:06.2f}.png")
    fig.savefig(fn, dpi=120)
    plt.close(fig)
    return fn


def _to_current_dd(ids):
    """ids converted to IMAS_VERSION when it was stored with another DD version."""
    if ids.ids_properties.version_put.data_dictionary != os.getenv("IMAS_VERSION"):
        ids = imas.convert_ids(ids, os.getenv("IMAS_VERSION"))
    return ids


def launch_points(uri):
    if uri is None:
        return None
    with imas.DBEntry(uri, "r") as db:
        ecl = _to_current_dd(db.get("ec_launchers", autoconvert=False))
        r = [float(np.asarray(b.launching_position.r)[0]) for b in ecl.beam]
        z = [float(np.asarray(b.launching_position.z)[0]) for b in ecl.beam]
    return np.array(r), np.array(z)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", required=True, help="input IMAS URI (equilibrium + core_profiles)")
    ap.add_argument("-o", "--output", required=True, help="output IMAS URI")
    ap.add_argument("--times", default="10:95:5", help="t0:t1:dt or comma list; nearest native slices are used")
    ap.add_argument(
        "--box",
        default=",".join(str(x) for x in DEFAULT_BOX),
        help="Rmin,Rmax,Zmin,Zmax [m] to be covered by the extended grid",
    )
    ap.add_argument("--mode", choices=list(MODES) + ["none"], default="matched")
    ap.add_argument("--plot", default=None, help="directory for diagnostic PNGs")
    ap.add_argument(
        "--launchers", default=None, help="URI with ec_launchers, to overlay the launch points in the plots"
    )
    args = ap.parse_args()
    box = [float(x) for x in args.box.split(",")]

    with imas.DBEntry(args.input, "r") as src:
        native = np.asarray(src.get("equilibrium", lazy=True, autoconvert=False).time)
        times = parse_times(args.times, native)
        print(f"{len(times)} slices: " + " ".join(f"{t:.2f}" for t in times))
        cp = _to_current_dd(src.get("core_profiles", autoconvert=False))
        lp = launch_points(args.launchers)
        if args.plot:
            os.makedirs(args.plot, exist_ok=True)

        with imas.DBEntry(args.output, "w") as dst:
            dst.put(cp)
            for k, t in enumerate(times):
                eq = _to_current_dd(src.get_slice("equilibrium", t, imas.ids_defs.CLOSEST_INTERP, autoconvert=False))
                if args.mode == "none":
                    (dst.put if k == 0 else dst.put_slice)(eq)
                    print(f"t={t:6.2f}s copied (no extension)")
                    continue
                info, diag = extend_slice(eq.time_slice[0], box, args.mode)
                info["t"] = float(eq.time[0])
                append_caveat(eq, args.mode, args.input)
                (dst.put if k == 0 else dst.put_slice)(eq)
                print(format_info(info))
                if args.plot:
                    print("   plot:", plot_slice(diag, info, lp, args.plot, args.mode))


if __name__ == "__main__":
    main()
