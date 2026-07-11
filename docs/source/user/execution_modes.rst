Execution Modes
===============

HCD Workflow currently has four supported launch modes. They share the same IMAS
input and output model but differ in where actor execution happens.

Mode Table
----------

.. list-table::
   :header-rows: 1
   :widths: 16 28 56

   * - Mode
     - Main entry point
     - What happens
   * - Legacy
     - ``workflow/workflow_driver.py CONFIG 0``
     - The driver opens IMAS, runs the time loop, calls ``HCDWorkflow.run()``,
       and iWrap actors execute in the same Python process.
   * - Hybrid M3
     - ``workflow/workflow_driver.py CONFIG 1`` plus ``hcd_workflow_m3.py``
     - The driver is a MUSCLE3 macro model. A single micro model receives IDS
       slices and then calls the same iWrap workflow internally.
   * - Pure M3
     - ``hcdworkflow/workflow_driver_m3_pure.py``
     - The driver talks directly to individual M3 actor executables. There is
       no iWrap workflow micro in the middle.
   * - Pure M3 + Rabbit
     - ``hcdwf_pure_rabbit_m3.ymmsl``
     - Extends Pure M3 with a stateful external GCC Rabbit NBI process.

Legacy
------

.. code-block:: text

   workflow_driver.py
     -> HCDWorkflow.run()
       -> iWrap actors
     -> IMAS output

Use Legacy mode as the baseline when debugging input data, actor parameters, or
output storage.

Hybrid M3
---------

.. code-block:: text

   workflow_driver.py      hcd_workflow_m3.py
   macro time loop  <----> micro workflow
   IMAS I/O                HCDWorkflow.run() -> iWrap actors

Hybrid mode validates the macro/micro MUSCLE3 boundary while keeping the actor
execution path close to legacy behavior.

Pure M3
-------

.. code-block:: text

          -> torbeam_m3.exe -> waves_ec
   driver -> cyrano_m3.exe  -> waves_ic
          -> merge_waves_m3.exe -> waves
          -> hcd2core_sources_m3.exe -> core_sources

Pure mode is the target architecture for direct actor coupling. The driver owns
IMAS I/O and the time loop. Each actor is a separate MUSCLE3 component.

The Rabbit variant adds ``rabbit_m3.exe`` as a separate GCC/foss process. Its
NBI waveform and code parameters are supplied locally rather than versioned
with HCDWF.

Validated Pure Subset
---------------------

As of 2026-06-10, the validated Pure M3 subset is:

* Multi-time-slice run.
* Single ``Ntor`` Cyrano path.
* EC branch through Torbeam.
* IC wave branch through Cyrano.
* ``merge_waves`` after EC and IC wave branches.
* ``hcd2core_sources`` post-processing.
* ``ic_wave_fp=0``: no FoPla in the benchmark chain.
* Rabbit EC+IC+NBI single-slice smoke with external local configuration.

The Pure driver also contains guards for zero-power slices:

* Skip Cyrano when IC launched power is zero.
* Skip FoPla when IC launched power is zero.
* Skip wave merging when one wave branch is inactive.

What Still Needs Care
---------------------

Treat these as validation targets, not routine production assumptions:

* Pure M3 FoPla full-chain runs.
* Weighted toroidal mode spectrum in Pure M3 mode.
* New direct actor combinations beyond the validated subset.
* Performance comparisons where mode weighting, FoPla selection, or time ranges
  are not identical.
