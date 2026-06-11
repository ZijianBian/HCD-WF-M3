Usage
=====

The workflow can be run through classic command wrappers, the unified Python
driver, or MUSCLE3 yMMSL files.

Command Summary
---------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Command
     - Use
   * - ``hcd_nogui -c CONFIG``
     - Classic console workflow entry point.
   * - ``hcdslice_nogui -c CONFIG``
     - Single-slice classic run.
   * - ``hcd_gui``
     - GUI for classic configuration editing and execution.
   * - ``python workflow/workflow_driver.py CONFIG 0``
     - Legacy in-process driver.
   * - ``python workflow/workflow_driver.py CONFIG 1``
     - Hybrid M3 macro component, normally launched by MUSCLE3.
   * - ``muscle_manager --start-all FILE.ymmsl``
     - Launch Hybrid or Pure M3 topology.
   * - ``./run.sh pure``
     - Launch the default Pure M3 no-FoPla topology.

Legacy Mode
-----------

.. code-block:: bash

   python workflow/workflow_driver.py tests/m3_hybrid 0

Legacy mode is useful when checking whether a problem is caused by physics
input, actor behavior, or M3 coupling.

Hybrid M3 Mode
--------------

.. code-block:: bash

   muscle_manager --start-all test_hybrid_hcdwf.ymmsl

Hybrid mode sends IDS slices between ``workflow_driver.py`` and
``hcd_workflow_m3.py``. The physics actors still run inside
``HCDWorkflow.run()`` through iWrap.

Pure M3 Mode
-------------------

Pure mode is launched from a yMMSL file that wires the macro driver directly to
actor executables.

.. code-block:: bash

   ./run.sh pure
   muscle_manager --start-all test_m3_pure_3actors.ymmsl

Use ``HCD_PURE_YMMSL`` to select another Pure topology:

.. code-block:: bash

   HCD_PURE_YMMSL=test_m3_pure_torbeam.ymmsl ./run.sh pure

Current validated Pure M3 actors:

* ``torbeam_m3.exe``
* ``cyrano_m3.exe``
* ``hcd2core_sources_m3.exe``

FoPla direct coupling exists in the driver but is not part of the validated
benchmark subset described in :doc:`validation`. The full experimental
topology including ``merge_waves`` and FoPla is kept in ``test_m3_pure.ymmsl``.

Output
------

The output IMAS run is controlled by ``input_workflow.xml``:

* ``output_user_or_path``
* ``output_database``
* ``output_backend``
* ``shot_nr``
* ``run_out``

MUSCLE3 also creates a run directory named like ``run_*``. It contains logs,
``configuration.ymmsl``, and the MUSCLE performance database when enabled.

Benchmark Rule
--------------

When comparing modes, keep the physics work identical. In particular, do not
compare a weighted multi-``Ntor`` legacy or hybrid run against a single-``Ntor``
Pure run.
