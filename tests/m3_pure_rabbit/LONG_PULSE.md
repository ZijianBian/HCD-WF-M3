# EC + IC + NBI long-pulse capability case

This case is the accepted Pure-M3 Rabbit reference extended over the ITER
105102 long pulse. It deliberately excludes FoPla.

## Actor chain

```text
Torbeam + Cyrano -> merge_waves ---+
Rabbit -> fast-ion IDSs -----------+-> hcd2core_sources
```

- ECRH: 80 Torbeam beams, up to 40 MW.
- ICRH: Cyrano, 42 MHz, 10 MW, effective single mode `Ntor = 35`.
- ICRH-NBI fast-ion coupling: disabled (`include_nbi = 0`).
- NBI: Rabbit, two 1 MeV deuterium injectors at 16.5 MW each.
- NBI geometry: `public/ITER_MD/130000/2301`.
- FoPla: disabled.

## Reference runs

The launcher keeps its original one-slice interface and accepts an optional
long-pulse range:

```bash
# Two-slice NBI transition pilot: stores 70 and 80 s.
bash tools/run_pure_m3_rabbit_reference.sh 269 70 90 10 80

# IC-off regression: stores 220 and 230 s.
bash tools/run_pure_m3_rabbit_reference.sh 271 220 240 10 220

# Accepted coarse long pulse: stores 30 slices from 10 through 300 s.
bash tools/run_pure_m3_rabbit_reference.sh 272 10 310 10 100
```

The Pure-M3 driver treats `tend` as exclusive. The accepted case therefore
uses `tend = 310 s` and does not evaluate the 310 s input slice, whose 105102
equilibrium has an invalid `global_quantities.magnetic_axis`. Run 271 verifies
that ICRH can turn off while the anonymous actor-generated NBI source remains
stored in the canonical `nbi` slot.

Validate and plot the completed long pulse with:

```bash
source ./config_hcd_iter_sdcc.sh
python tools/validate_hcd_long_pulse.py --run 272
python tools/plot_hcd_long_pulse.py --run 272
```

The plotter reads launched powers from the three `*waveforms.yaml` files,
coupled power, electron/ion power partition, and driven current from
`core_sources`, and Rabbit particle sources from `distribution_sources`. It
produces the capability dashboards, radial profiles, particle evolution, CSV
data, and a Markdown summary without smoothing, regridding, or repairing actor
output values.
