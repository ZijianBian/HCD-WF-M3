Pure M3 Driver
=====================

Pure M3 mode is implemented by:

.. code-block:: text

   hcdworkflow/workflow_driver_m3_pure.py

The driver is a MUSCLE3 macro component. It opens IMAS databases, owns the time
loop, and sends IDS messages directly to actor executables.

Actor Registry
--------------

The driver keeps a port registry named ``ACTOR_PORTS``. Each actor has:

* ``send`` ports used by the driver.
* ``recv`` ports read by the driver.

Current actors in the registry:

.. list-table::
   :header-rows: 1

   * - Actor key
     - Output to driver
     - Notes
   * - ``torbeam``
     - ``waves_in``
     - EC wave branch.
   * - ``cyrano``
     - ``waves_ic_in``
     - IC wave branch.
   * - ``rabbit``
     - ``distribution_sources_rabbit_in``, ``distributions_rabbit_in``
     - Stateful NBI fast-ion branch; enabled together with ``nbi_fp=1``.
   * - ``fopla``
     - ``distributions_in``
     - Optional IC FP branch.
   * - ``merge_waves``
     - ``waves_merged_in``
     - Runs only when both wave branches are active.
   * - ``hcd2core_sources``
     - ``core_sources_in``
     - Post-processing branch.

Validated No-FoPla Topology
---------------------------

.. code-block:: text

   driver.equilibrium_out      -> torbeam.equilibrium_in
   driver.core_profiles_out    -> torbeam.core_profiles_in
   driver.ec_launchers_out     -> torbeam.ec_launchers_in
   torbeam.waves_out           -> driver.waves_in

   driver.*_ic                 -> cyrano.*
   cyrano.waves_out            -> driver.waves_ic_in

   driver.waves_ec_out         -> merge_waves.waves1_in
   driver.waves_ic_out         -> merge_waves.waves2_in
   merge_waves.waves_out       -> driver.waves_merged_in

   driver.*_post               -> hcd2core_sources.*
   hcd2core_sources.core_sources_out -> driver.core_sources_in

Power Gating
------------

``POWER_EPS_W`` is used to decide whether a branch is active.

If IC launched power is zero:

* Cyrano is skipped.
* FoPla is skipped.
* ``merge_waves`` is skipped and the EC waves are carried forward.

If EC power is zero and IC is active:

* ``merge_waves`` is skipped and the IC waves are carried forward.

Rabbit is different from the wave solvers: when connected and selected with
``nbi_fp=1``, it runs on every time slice so that its reuse/state protocol is
not broken by a zero-power slice.

Rabbit GCC Compatibility
------------------------

The validated SDCC build keeps Rabbit in a separate GCC process while matching
the HCD workflow's wire/data contract:

* GCC 13.2 / ``foss-2023b``.
* IMAS-Fortran 5.5.0, DD 4.1.0.
* MUSCLE3 0.8.0.
* Executable: ``$ACTOR_FOLDER/rabbit/rabbit_m3.exe``.
* Runtime launcher: ``tools/run_rabbit_m3_gcc_2023b.sh``.

Do not mix this topology with the collaborator's DD 4.1.1/MUSCLE3 0.10 binary;
the MUSCLE wire versions are not compatible. The reference topology is
``pure_m3_rabbit_no_fopla.ymmsl`` and requires ``nbi_fp=1`` in
``input_workflow.xml``.

.. code-block:: bash

   bash tools/run_pure_m3_rabbit_reference.sh 249

The argument is a free output run number. The launcher stages the tracked
reference fixture, resolves repository/actor paths, sources
``config_hcd_iter_sdcc.sh``, captures the manager log, and invokes the DD4
validator. The latest accepted result is ``105102/249@100 s``.

Build and run logs are retained under
``$ACTOR_FOLDER/rabbit/logs``. The accepted three-actor run is
``pure_m3_torbeam_cyrano_rabbit_run249_20260711_042028.log``.

FoPla Input Choice
------------------

FoPla is an IC Fokker-Planck actor. The driver feeds FoPla the IC wave branch,
not the merged EC+IC waves. This avoids selecting an EC wave inside FoPla's RF
interpolation path.

Adding a New Direct Actor
-------------------------

1. Add the actor ports to ``ACTOR_PORTS``.
2. Add the yMMSL component and conduits.
3. Add settings for actor code parameters.
4. Add branch logic in the driver time loop.
5. Validate one slice first, then a short multi-slice case, then the reference
   benchmark style case.
