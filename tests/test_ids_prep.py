"""Unit tests for pure helpers in `workflow/ids_prep.py`.

Currently covers `ic_antenna_n_phi_weights`, the antenna toroidal-mode
(`n_phi`) power-weight spectrum used to replace the single-`Ntor` CYRANO
input with a realistic multi-mode spectrum.

These tests use lightweight duck-typed stand-ins for the `ic_antennas`
IDS rather than a real IMAS IDS: the function only does plain attribute
and index access, so fakes exercise the real logic without a database.
"""

import math
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import ids_prep
from workflow.ids_prep import ic_antenna_n_phi_weights, merge_ic_wave_modes


class _ArrayField:
    def __init__(self, values=()):
        self.values = np.asarray(values, dtype=float)

    @property
    def has_value(self):
        return self.values.size > 0

    def __len__(self):
        return len(self.values)

    def __array__(self, dtype=None):
        return np.asarray(self.values, dtype=dtype)


# --- fake ic_antennas IDS builders -----------------------------------------

def _strap(phase, phi, phase_time=None):
    """A fake strap with a time-dependent `phase` signal and `outline.phi`."""
    return SimpleNamespace(
        phase=SimpleNamespace(data=np.atleast_1d(phase),
                              time=np.atleast_1d(phase_time)
                              if phase_time is not None else np.array([])),
        outline=SimpleNamespace(phi=np.atleast_1d(phi)),
    )


def _antenna(straps):
    """A fake single-module antenna wrapping the given straps."""
    return SimpleNamespace(antenna=[
        SimpleNamespace(module=[SimpleNamespace(strap=straps)])
    ])


# DT_baseline_example/ic_waveforms.yaml: 2-strap dipole antenna.
DT_DPHI = 0.0836447165337165


def _dt_baseline_antenna():
    """The DT_baseline 2-strap dipole antenna (phases [0, pi])."""
    return _antenna([
        _strap(phase=0.0, phi=0.0),
        _strap(phase=math.pi, phi=-DT_DPHI),
    ])


# --- tests -----------------------------------------------------------------

def test_dt_baseline_matches_sin2_array_factor():
    """2-strap dipole: w_n must follow w_n ~ sin^2(n*dphi/2)."""
    n_phi, weight = ic_antenna_n_phi_weights(_dt_baseline_antenna(), n_max=80)

    expected = np.sin(n_phi * DT_DPHI / 2.0) ** 2
    expected = expected / expected.sum()
    np.testing.assert_allclose(weight, expected, atol=1e-12)


def test_dt_baseline_peak_near_37():
    """Dipole array-factor peak sits at |n| ~ pi/dphi ~ 37.6."""
    n_phi, weight = ic_antenna_n_phi_weights(_dt_baseline_antenna(), n_max=80)

    peak_n = abs(int(n_phi[np.argmax(weight)]))
    assert peak_n == round(math.pi / DT_DPHI)  # 38


def test_dt_baseline_weight_is_symmetric_in_n():
    """For the DT dipole antenna w_n is even in n (cos is even).

    This evenness holds for in-phase / anti-phase (0 or pi) strap phasing,
    not for an arbitrary 2-strap antenna.
    """
    n_phi, weight = ic_antenna_n_phi_weights(_dt_baseline_antenna(), n_max=80)

    by_n = dict(zip(n_phi.tolist(), weight.tolist()))
    for n in range(1, 81):
        assert by_n[n] == pytest.approx(by_n[-n], abs=1e-12)


def test_dt_baseline_zero_mode_vanishes():
    """Dipole phasing launches no power into n=0."""
    n_phi, weight = ic_antenna_n_phi_weights(_dt_baseline_antenna(), n_max=80)
    assert weight[np.where(n_phi == 0)[0][0]] == pytest.approx(0.0, abs=1e-12)


def test_weight_is_normalized():
    n_phi, weight = ic_antenna_n_phi_weights(_dt_baseline_antenna(), n_max=80)
    assert weight.sum() == pytest.approx(1.0, abs=1e-12)


def test_monopole_phasing_peaks_at_zero():
    """Equal strap phases (monopole) concentrate power near n=0."""
    monopole = _antenna([
        _strap(phase=0.0, phi=0.0),
        _strap(phase=0.0, phi=-DT_DPHI),
    ])
    n_phi, weight = ic_antenna_n_phi_weights(monopole, n_max=80)
    assert int(n_phi[np.argmax(weight)]) == 0


def test_explicit_n_values_subset():
    """Caller-supplied n grid is honoured and re-normalized over that set."""
    sample = [-38, -35, 35, 38]
    n_phi, weight = ic_antenna_n_phi_weights(
        _dt_baseline_antenna(), n_values=sample)
    assert n_phi.tolist() == sample
    assert weight.sum() == pytest.approx(1.0, abs=1e-12)


def test_phase_signal_sampled_at_time():
    """A time-dependent strap phase is read at the requested time slice."""
    # strap1 phase flips 0 -> pi between t=10 and t=60.
    antenna = _antenna([
        _strap(phase=0.0, phi=0.0),
        _strap(phase=[0.0, math.pi], phi=-DT_DPHI, phase_time=[10.0, 60.0]),
    ])
    # At t=60 this is the dipole antenna -> n=0 weight vanishes.
    _, w_dipole = ic_antenna_n_phi_weights(antenna, time=60.0, n_max=80)
    # At t=10 both straps are in phase (monopole) -> n=0 weight is maximal.
    n_phi, w_mono = ic_antenna_n_phi_weights(antenna, time=10.0, n_max=80)
    zero_idx = np.where(n_phi == 0)[0][0]
    assert w_dipole[zero_idx] == pytest.approx(0.0, abs=1e-12)
    assert int(n_phi[np.argmax(w_mono)]) == 0


def test_no_strap_data_falls_back_to_zero_mode():
    """An empty antenna yields all weight on n=0."""
    empty = SimpleNamespace(antenna=[SimpleNamespace(module=[])])
    n_phi, weight = ic_antenna_n_phi_weights(empty, n_max=10)
    assert weight[np.where(n_phi == 0)[0][0]] == pytest.approx(1.0)
    assert weight.sum() == pytest.approx(1.0)


# --- _n_phi_values() Ntor-sign regression ----------------------------------

@pytest.mark.parametrize("ntor, expected", [(-35, [-35]), (35, [35]), (0, [0])])
def test_n_phi_values_keeps_negative_ntor(monkeypatch, ntor, expected):
    """Regression: a negative single `Ntor` must survive `_n_phi_values()`.

    The earlier `ntor and ntor > 0` guard silently dropped `Ntor=-35`
    back to `[0]`, which would lose negative-n / symmetric-spectrum runs.
    """
    monkeypatch.setattr(ids_prep, "_xml_int", lambda *a, **k: ntor)
    result = ids_prep._n_phi_values(waves=None, config_folder_path="dummy")
    assert result.tolist() == expected


def test_n_phi_values_prefers_configured_toroidal_modes(monkeypatch, tmp_path):
    """Placeholder n_phi axes should match ic_toroidal_modes.yaml when present."""
    if ids_prep.yaml is None:
        pytest.skip("PyYAML is not available")
    (tmp_path / "ic_toroidal_modes.yaml").write_text(
        "enabled: true\n"
        "modes:\n"
        "  - n_phi: 55\n"
        "    weight: 0.5\n"
        "  - n_phi: -55\n"
        "    weight: 0.5\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ids_prep, "_xml_int", lambda *a, **k: 35)

    result = ids_prep._n_phi_values(waves=None, config_folder_path=str(tmp_path))

    assert result.tolist() == [55, -55]


# --- equilibrium FoPla input fix-up -----------------------------------------

def test_eq_fill_rho_tor_from_flux_uses_absolute_b0_and_phi_delta():
    b0 = -2.0
    expected_rho_tor = np.array([0.0, 1.0, 2.0])
    phi = -np.pi * abs(b0) * expected_rho_tor ** 2
    p1d = SimpleNamespace(
        rho_tor=_ArrayField(),
        rho_tor_norm=_ArrayField([0.0, 0.5, 1.0]),
        phi=_ArrayField(phi),
    )
    ts = SimpleNamespace(profiles_1d=p1d)
    eq = SimpleNamespace(
        vacuum_toroidal_field=SimpleNamespace(b0=_ArrayField([b0]))
    )

    ids_prep._eq_fill_rho_tor_from_flux(eq, ts)

    np.testing.assert_allclose(p1d.rho_tor, expected_rho_tor)


# --- merge_ic_wave_modes ----------------------------------------------------

def _fake_waves(n_phi, power, current, profile):
    """Minimal duck-typed waves IDS for the pure merge helper."""
    profile = np.asarray(profile, dtype=float)
    gq = SimpleNamespace(
        n_phi=np.asarray([n_phi]),
        power=float(power),
        power_n_phi=np.asarray([power], dtype=float),
        current_phi=float(current),
        current_phi_n_phi=np.asarray([current], dtype=float),
        electrons=SimpleNamespace(
            power_thermal=0.4 * float(power),
            power_thermal_n_phi=np.asarray([0.4 * float(power)]),
        ),
        ion=[],
    )
    p1d = SimpleNamespace(
        n_phi=np.asarray([n_phi]),
        power_density=profile,
        power_density_n_phi=profile[np.newaxis, :],
        current_parallel_density=profile * float(current) / 1000.0,
        current_parallel_density_n_phi=(profile * float(current) / 1000.0)[np.newaxis, :],
        power_inside=np.cumsum(profile),
        power_inside_n_phi=np.cumsum(profile)[np.newaxis, :],
        current_phi_inside=np.cumsum(profile) * float(current) / 1000.0,
        current_phi_inside_n_phi=(np.cumsum(profile) * float(current) / 1000.0)[np.newaxis, :],
        electrons=SimpleNamespace(
            power_density_thermal=0.4 * profile,
            power_density_thermal_n_phi=(0.4 * profile)[np.newaxis, :],
            power_inside_thermal=0.4 * np.cumsum(profile),
            power_inside_thermal_n_phi=(0.4 * np.cumsum(profile))[np.newaxis, :],
        ),
        ion=[],
        e_field_n_phi=[],
    )
    wave = SimpleNamespace(
        global_quantities=[gq],
        profiles_1d=[p1d],
        profiles_2d=[],
    )
    return SimpleNamespace(
        ids_properties=SimpleNamespace(homogeneous_time=1),
        coherent_wave=[wave],
    )


def test_merge_ic_wave_modes_writes_two_n_phi_slots():
    plus = _fake_waves(55, power=10.0, current=100.0, profile=[1.0, 3.0])
    minus = _fake_waves(-55, power=10.0, current=-60.0, profile=[5.0, 7.0])

    merged = merge_ic_wave_modes([plus, minus], [55, -55], [0.5, 0.5])
    wave = merged.coherent_wave[0]
    gq = wave.global_quantities[0]
    p1d = wave.profiles_1d[0]

    assert gq.n_phi.tolist() == [55, -55]
    np.testing.assert_allclose(gq.power_n_phi, [5.0, 5.0])
    assert gq.power == pytest.approx(10.0)
    np.testing.assert_allclose(gq.current_phi_n_phi, [50.0, -30.0])
    assert gq.current_phi == pytest.approx(20.0)

    assert p1d.n_phi.tolist() == [55, -55]
    np.testing.assert_allclose(p1d.power_density, [3.0, 5.0])
    np.testing.assert_allclose(
        p1d.power_density_n_phi,
        [[0.5, 1.5], [2.5, 3.5]],
    )
