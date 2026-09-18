Choosing an execution mode
==========================

Choose a mode based on the actors you have installed and how you want to couple
them. A mode change does not select the physics for you: the saved actor
parameters and workflow configuration still define the calculation.

.. list-table::
   :header-rows: 1
   :widths: 15 45 40

   * - Mode
     - How it runs
     - Use it when
   * - Legacy
     - Calls the iWrap workflow directly.
     - You want to run an existing standalone iWrap case.
   * - Hybrid
     - Exchanges IDS slices between a MUSCLE3 driver and the iWrap workflow.
     - You need a MUSCLE3 interface around the existing workflow.
   * - Pure
     - Connects a MUSCLE3 driver to individual native actor executables.
     - You have the native actors and a matching topology.

Launch from the repository root with your saved configuration:

.. code-block:: bash

   ./run.sh legacy /path/to/config
   ./run.sh hybrid /path/to/config
   ./run.sh pure /path/to/config

Hybrid uses ``topologies/hybrid.ymmsl``. Pure uses
``topologies/pure.ymmsl``. The launcher makes a run-specific copy tied to
your configuration folder; see :doc:`usage` for its location.

Choose the Pure actors
----------------------

Select the actors in ``input_workflow.xml`` under ``actor_selection``.
The single ``topologies/pure.ymmsl`` template supports TORBEAM, CYRANO,
Rabbit, FoPla, wave merging and ``hcd2core_sources``. At launch, it is reduced
to the components and connections needed by the saved configuration; the
source template stays unchanged.

Rabbit needs its separate GCC actor build. FoPla needs an installed
``fopla_m3.exe``. Rabbit and FoPla cannot currently be used together in
Pure mode. Native actor requirements are in
:doc:`../developer/actor_installation`.

Unsupported selections or missing parameter files stop the launcher before
MUSCLE3 starts. A custom topology must provide every selected actor; unused
actor components are removed from the generated run configuration.

Parallel EC and IC
------------------

Pure runs EC and IC serially by default. Independent TORBEAM and CYRANO
calculations can overlap when ``pure_parallel_ec_ic: true`` is added to the
topology's ``settings``.

This requires explicit CYRANO settings that do not depend on EC waves or
fast-particle inputs, and excludes Rabbit and FoPla. Follow the parameter
checks in :doc:`../developer/architecture` before enabling it. Time slices
still run in sequence.
