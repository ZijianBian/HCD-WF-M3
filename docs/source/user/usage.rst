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
   * - ``muscle_manager --run-dir DIR --start-all FILE.ymmsl``
     - Launch Hybrid or Pure M3 topology.
   * - ``./run.sh pure``
     - Launch the default Pure M3 topology.

Legacy Mode
-----------

.. code-block:: bash

   python workflow/workflow_driver.py tests/m3_hybrid 0

Legacy mode is useful when checking whether a problem is caused by physics
input, actor behavior, or M3 coupling.

Hybrid M3 Mode
--------------

.. note::

   Always pass ``--run-dir`` when calling ``muscle_manager`` directly.  Without
   it MUSCLE3 creates ``run_<model>_<timestamp>/`` in the current working
   directory, which quickly clutters the repository root.  The directory must
   already exist, so create it first.  ``./run.sh`` does this for you and keeps
   each run under ``runs/``.

.. code-block:: bash

   RUN_DIR=runs/hybrid_$(date +%Y%m%d_%H%M%S)
   mkdir -p "$RUN_DIR"
   muscle_manager --run-dir "$RUN_DIR" --start-all test_hybrid_hcdwf.ymmsl

Hybrid mode sends IDS slices between ``workflow_driver.py`` and
``hcd_workflow_m3.py``. The physics actors still run inside
``HCDWorkflow.run()`` through iWrap.

Pure M3 Mode
-------------------

Pure mode is launched from a yMMSL file that wires the macro driver directly to
actor executables.

.. code-block:: bash

   ./run.sh pure

   # or, launching MUSCLE3 directly:
   RUN_DIR=runs/pure_$(date +%Y%m%d_%H%M%S)
   mkdir -p "$RUN_DIR"
   muscle_manager --run-dir "$RUN_DIR" --start-all pure_m3_no_fopla.ymmsl

Use ``HCD_PURE_YMMSL`` to select Rabbit, FoPla, or a local custom topology:

.. code-block:: bash

   HCD_PURE_YMMSL=local_case.ymmsl ./run.sh pure
   HCD_PURE_YMMSL=pure_m3_rabbit_no_fopla.ymmsl ./run.sh pure

Current validated Pure M3 actors:

* ``torbeam_m3.exe``
* ``cyrano_m3.exe``
* ``merge_waves_m3.exe``
* ``rabbit_m3.exe``
* ``hcd2core_sources_m3.exe``

The maintained default is ``pure_m3_no_fopla.ymmsl``. Rabbit is wired in
``pure_m3_rabbit_no_fopla.ymmsl``; FoPla remains available through the optional
``test_m3_pure.ymmsl`` topology.

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
