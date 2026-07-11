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
   * - ``fopla``
     - ``distributions_in``
     - Optional IC FP branch.
   * - ``rabbit``
     - ``distribution_sources_rabbit_in``, ``distributions_rabbit_in``
     - Stateful NBI fast-ion branch in a separate GCC process.
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

EC and IC are independent selections. Wave and core-source counts come from
the selected IDS configuration, and the driver preserves actor output order;
it does not impose EC-before-IC ordering.

Rabbit NBI Branch
-----------------

``hcdwf_pure_rabbit_m3.ymmsl`` adds Rabbit before Cyrano and post-processing.
Rabbit receives ``core_profiles``, ``equilibrium``, ``nbi``, ``wall``, and a
minimal ``workflow`` IDS. Its ``distributions`` and ``distribution_sources``
are forwarded to downstream actors.

The Rabbit topology and ``nbi_fp=1`` must be selected together. Rabbit is
stateful and is advanced on every time slice, including zero-NBI-power slices.
It cannot currently be connected together with FoPla because the Pure driver
does not yet merge their distribution outputs.

The reference NBI waveform and Rabbit code parameters are intentionally not
versioned. Provide them locally under ``tests/m3_pure_rabbit`` before launching
the Rabbit topology.

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
