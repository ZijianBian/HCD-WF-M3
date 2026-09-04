# Rabbit DD 4.1.0 / HCDWF compatibility

## Summary

This merge request contains the minimum source changes needed to build and run
Rabbit in the HCD workflow with DD 4.1.0, MUSCLE3 0.8.0 and GCC 13.2.

It intentionally excludes the broader defensive checks and the MUSCLE3 wall-port
receive reordering from the earlier local patch. Those changes are not required
for successful execution and should be reviewed separately if desired.

## Changes

1. Iterate over all `core_profiles.profiles_1d(:)%ion` entries and compactly index
   hydrogen isotopes and impurities. DD4 input does not guarantee that hydrogen
   isotopes occupy the first contiguous positions in `ion(:)`.
2. Use `grid%rho_tor_norm` directly for volume interpolation. The tested DD4
   scenario populates `rho_tor_norm` but not `rho_tor`.
3. Populate `collisions%ion(1)%element(1)%a` and `%z_n` in the output
   `distributions` IDS.
4. Replace local `ASSOCIATE` aliases in `fnbcd_redl` with direct derived-type
   component references. This preserves the vector expressions and avoids a
   reproducible GCC 13.2 front-end internal compiler error.

## Commit structure

- `c286ca6` — Fix DD4 plasma species and radial-grid mapping
- `903e063` — Populate collision-ion species metadata
- `8d9ce5b` — Avoid GCC 13.2 ICE in Redl current calculation

Base revision: `e99ad70` (`origin/master`, merge of
`feature/DD4_IMAS_Python`, 2026-07-31).

## Build validation

Clean build completed with:

- `IMAS-Fortran/5.5.0-foss-2023b-DD-4.1.0`
- `XMLlib/3.3.2-GCC-13.2.0`
- `INTERPOS/9.2.0-gfbf-2023b`
- `MUSCLE3/0.8.0-foss-2023b`
- GCC 13.2

The following targets built successfully:

- `rabbitA_imas`
- `rabbit_imas.exe`
- `rabbit_m3.exe`

## Workflow validation

The final executable completed the ITER shot `105102`, time `100 s`, Pure M3
HCD workflow as IMAS output run `312`. Rabbit, TORBEAM, CYRANO, merge_waves,
HCD2CORE_SOURCES and the workflow driver all exited with code 0; MUSCLE3 reported
that the simulation finished without error.

The DD4 output validator passed for all four output IDS:

- `waves`: 81 wave entries, IC `n_phi = 35`
- `core_sources`: EC, IC and NBI sources present
- `distributions`: populated
- `distribution_sources`: populated

A numerical comparison against control run `311`, produced with the previously
validated scalar-loop workaround, passed at relative tolerance `3e-4`. EC and IC
quantities were identical. The maximum Rabbit/NBI relative difference was
`1.986444e-4`; aggregate NBI core-source differences were at most
`6.719640e-5`.

Rabbit has an unseeded Fortran intrinsic `random_number` call in `IDAbesrad.F90`.
Two runs of the same control executable differ by as much as `1.347936e-4`, so a
`1e-4` threshold is below the observed same-binary stochastic floor. Adding a
deterministic test seed is deliberately outside this compatibility patch.

## Known non-blocking issue

The unmodified upstream `rabbit_m3.f90` emits MUSCLE3 MMSF sequence warnings for
the wall `F_INIT` receive order, but the tested workflow completes. Reordering
that port is therefore not a hard DD4 compatibility requirement and is excluded
from this minimal MR. It can be proposed separately as a protocol-cleanup change.
