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
     - Launch the default Pure M3 topology.
   * - ``./run.sh pure-rabbit``
     - Launch Pure M3 with the external Rabbit NBI actor and a local case.

Legacy Mode
-----------

.. code-block:: bash

   python workflow/workflow_driver.py tests/m3_hybrid 0

Legacy mode is useful when checking whether a problem is caused by physics
input, actor behavior, or M3 coupling.

Hybrid M3 Mode
--------------

.. code-block:: bash

   muscle_manager --start-all hcdwf_hybrid_m3.ymmsl

Hybrid mode sends IDS slices between ``workflow_driver.py`` and
``hcd_workflow_m3.py``. The physics actors still run inside
``HCDWorkflow.run()`` through iWrap.

Pure M3 Mode
-------------------

Pure mode is launched from a yMMSL file that wires the macro driver directly to
actor executables.

.. code-block:: bash

   ./run.sh pure
   muscle_manager --start-all hcdwf_pure_m3.ymmsl

Use ``HCD_PURE_YMMSL`` only when testing a local custom topology:

.. code-block:: bash

   HCD_PURE_YMMSL=local_case.ymmsl ./run.sh pure

Current validated Pure M3 actors:

* ``torbeam_m3.exe``
* ``cyrano_m3.exe``
* ``merge_waves_m3.exe``
* ``hcd2core_sources_m3.exe``

The maintained Pure baseline is kept in ``hcdwf_pure_m3.ymmsl``.

Pure M3 with Rabbit
-------------------

``hcdwf_pure_rabbit_m3.ymmsl`` adds the external Rabbit actor. The repository
contains the coupling and GCC runtime launcher, but not the NBI reference case.
Before running, provide ``tests/m3_pure_rabbit`` locally with
``input_workflow.xml``, ``nbi_waveforms.yaml``, and Rabbit XML/namelist files.

.. code-block:: bash

   source config_hcd_iter_sdcc.sh
   ./run.sh pure-rabbit

The normal environment locates Rabbit through ``ACTOR_FOLDER``. Rabbit then
loads its GCC/foss modules in its own process through
``tools/run_rabbit_m3_gcc_2023b.sh``.

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
