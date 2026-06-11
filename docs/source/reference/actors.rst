Actors
======

This page lists the actors most relevant to the current M3 work.

Core Actors in the Validated Benchmark
--------------------------------------

.. list-table::
   :header-rows: 1

   * - Process
     - Actor
     - Role
   * - EC wave solver
     - Torbeam
     - Computes EC wave deposition.
   * - IC wave solver
     - Cyrano
     - Computes IC wave response for a selected toroidal mode.
   * - Wave merger
     - merge_waves
     - Combines EC and IC waves when both branches are active.
   * - Source filler
     - hcd2core_sources
     - Converts HCD outputs into ``core_sources``.

Optional or Not Yet Fully Validated in Pure Mode
------------------------------------------------

.. list-table::
   :header-rows: 1

   * - Actor
     - Note
   * - FoPla
     - IC Fokker-Planck branch wired in ``test_m3_pure.ymmsl``. It requires
       the matching M3 actor executable and code-parameter XML.
   * - NBI actors
     - Classic workflow support exists. Direct Pure M3 coverage needs separate
       validation.
   * - Additional EC/IC solvers
     - Classic workflow support exists. Direct Pure M3 coverage depends on
       available actor executables and yMMSL wiring.

Classic Actor Selection
-----------------------

Classic ``input_workflow.xml`` actor values are integer selections from each
``list`` attribute. ``0`` disables a process.

Example:

.. code-block:: xml

   <ic_wave_solver display="Wave solver" list="cyrano tomcat pion lion">1</ic_wave_solver>

Pure M3 Actor Requirements
--------------------------

Pure M3 mode needs M3 actor executables, for example:

.. code-block:: text

   /path/to/PYTHON_ACTORS/torbeam/torbeam_m3.exe
   /path/to/PYTHON_ACTORS/cyrano/cyrano_m3.exe

The yMMSL file must list each component, its ports, conduits, resources, and
implementation executable.
