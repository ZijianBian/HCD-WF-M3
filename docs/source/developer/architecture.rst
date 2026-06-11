Architecture
============

The workflow has one IMAS data model and three execution layouts.

Shared Responsibilities
-----------------------

All modes need to:

* Read scenario IDS slices from IMAS.
* Prepare machine IDS inputs.
* Execute selected HCD actors.
* Merge or post-process outputs.
* Write output IDS slices back to IMAS.

Legacy Layout
-------------

.. code-block:: text

   workflow_driver.py
     setup_databases()
     time loop
       get_ids_slices()
       HCDWorkflow.run()
         WorkflowExecutor
           iWrap actors
       store_ids_slices()

There is no MUSCLE3 boundary in Legacy mode.

Hybrid M3 Layout
----------------

.. code-block:: text

   workflow_driver.py                         hcd_workflow_m3.py
   ------------------                         ------------------
   IMAS open/read/write                       HCDWorkflow.initialize()
   time loop                                  reuse loop
   send IDS on O_I ports  ----------------->  receive IDS on F_INIT ports
   receive IDS on S ports  <----------------  send IDS on O_F ports

Hybrid mode introduces one macro/micro boundary. The micro still runs the
classic iWrap actor chain.

Pure M3 Layout
--------------

.. code-block:: text

   workflow_driver_m3_pure.py
     -> torbeam_m3.exe
     -> cyrano_m3.exe
     -> fopla_m3.exe             optional, not in validated benchmark subset
     -> merge_waves_m3.exe
     -> hcd2core_sources_m3.exe

Pure mode removes the ``HCDWorkflow.run()`` micro and makes each actor visible
to MUSCLE3.

Important Modules
-----------------

.. list-table::
   :header-rows: 1

   * - Module
     - Role
   * - ``workflow.workflow_driver``
     - Database setup, time range resolution, IDS read/write, Legacy and
       Hybrid macro execution.
   * - ``hcdworkflow.hcd_workflow_m3``
     - Hybrid micro component.
   * - ``hcdworkflow.workflow_driver_m3_pure``
     - Pure M3 actor driver.
   * - ``workflow.ids_prep``
     - DD compatibility fix-ups, EC/IC waveform helpers, and toroidal mode
       utilities.
   * - ``hcdworkflow.workflow_executor``
     - Classic actor execution and dependency handling.

Data Boundaries
---------------

M3 messages contain serialized IDS objects. The explicit transfer time is small
in the current benchmark, but each boundary also adds actor handshakes,
deserialization, IDS preparation, logging, and scheduling.

Power-Gated Branches
--------------------

The Pure driver checks launched power before sending actor messages:

* EC power determines whether the EC wave branch is useful.
* IC power determines whether Cyrano and FoPla should run.
* ``merge_waves`` runs only when both EC and IC wave branches are active.

This avoids running FoPla after IC power is off and avoids merging empty wave
branches.
