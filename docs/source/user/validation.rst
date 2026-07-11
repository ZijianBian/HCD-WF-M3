Validation Status
=================

This page records the current M3 validation state. It is intentionally short
and should be updated whenever a new reference case becomes the preferred one.

Pure M3 Fixes
-------------

Two fixes made Pure mode pass the zero-IC transition cases:

* Cyrano and FoPla are gated by launched IC power.
* ``merge_waves`` is skipped when one wave branch is inactive.

This matters because FoPla can renormalize to its XML target power even when
the IC waveform is off, and merging an empty branch can fail on transition
slices.

DD4 HCD Output Contract
-----------------------

The current Hybrid and Pure baselines were validated with EC-only, IC-only,
combined EC+IC, IC-off, and fully inactive HCD slices. Source counts are read
from ``ec_launchers`` and ``ic_antennas``; neither source requires the other.
Inactive slices retain the actor-established schema and ``n_phi`` dimensions.
Actor output order is preserved and is not part of the validation contract.

Validated Pure Scenarios
------------------------

.. list-table::
   :header-rows: 1

   * - Scenario
     - Coverage
     - Result
   * - Pure multi-slice run
     - EC Torbeam, IC Cyrano, merge_waves, FoPla, hcd2core_sources
     - Passed.
   * - Pure zero-IC transition run
     - Cyrano/FoPla power gating and inactive-branch wave merge
     - Passed after inactive-branch merge guard.
   * - Pure single-``Ntor`` timing run
     - Same physics options as the corrected Legacy and Hybrid timing runs
     - Passed.
   * - Pure Rabbit NBI smoke, ``ITER/4/105102/268`` at ``100 s``
     - Torbeam, Cyrano, Rabbit, merge_waves, and hcd2core_sources; Rabbit GCC
       process with Intel HCD actors over MUSCLE3 0.8/DD 4.1.0
     - Passed: 81 waves, 2 distributions, 2 distribution_sources, and an NBI
       core source; all checked numeric fields were finite and sentinel-free.

The Rabbit waveform and code-parameter files used for that smoke test are kept
outside the versioned repository. The result demonstrates the integration but
is not a bundled public reference case.

Corrected Runtime Benchmark Snapshot
------------------------------------

The corrected timing comparison used identical physics settings across the
three modes.

Common settings:

* Time range: ``10`` to ``320 s``.
* Time step: ``dt=5 s``.
* 62 slices.
* EC actor: Torbeam.
* IC actor: Cyrano.
* FoPla off: ``ic_wave_fp=0``.
* ``fill_core_sources=1``.
* Single Cyrano ``Ntor=35``.
* Weighted toroidal modes disabled for the corrected comparison.

.. list-table::
   :header-rows: 1

   * - Mode
     - Elapsed
   * - Legacy
     - ``3848 s`` or ``1:04:08``
   * - Hybrid
     - ``4026 s`` or ``1:07:06``
   * - Pure
     - ``3975 s`` or ``1:06:15``

The three modes are close once the physics work is identical. These numbers
are a benchmark snapshot, not a universal performance guarantee.

Invalidated Benchmark
---------------------

An earlier benchmark should not be used for runtime conclusions. Legacy and
Hybrid ran weighted ``Ntor=-38/+38`` Cyrano work while Pure M3 used a
single Cyrano path. That made the comparison unfair.

Performance Interpretation
--------------------------

M3 overhead is usually small compared with physics actor time. In a fair timing
run, split the wall time into physics actor time and workflow overhead:

.. list-table::
   :header-rows: 1

   * - Mode
     - Physics / actor critical path
     - Driver IDS/IMAS and local work
     - Explicit M3 transfer
     - M3 setup/cleanup
   * - Legacy
     - ``~3627 s``
     - ``~221 s``
     - ``0 s``
     - ``0 s``
   * - Hybrid
     - ``3798 s``
     - ``221 s``
     - ``4 s``
     - ``4 s``
   * - Pure
     - ``3679 s``
     - ``271 s``
     - ``12 s``
     - ``13 s``

``RECEIVE_WAIT`` in MUSCLE logs is not pure overhead. It often means the driver
is waiting while Torbeam, Cyrano, or hcd2core_sources is doing physics work.
