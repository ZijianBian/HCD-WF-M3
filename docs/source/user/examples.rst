Examples
========

This page keeps only the examples that are useful for the current branch.

Legacy Baseline
---------------

Use this when you need to check that the input case and actors work before
adding MUSCLE3 coupling.

.. code-block:: bash

   source config_hcd_iter_sdcc.sh
   python workflow/workflow_driver.py tests/m3_hybrid 0

Hybrid M3
---------

Use this to exercise the macro-to-workflow M3 boundary.

.. code-block:: bash

   source config_hcd_iter_sdcc.sh
   RUN_DIR=runs/hybrid_$(date +%Y%m%d_%H%M%S)
   mkdir -p "$RUN_DIR"
   muscle_manager --run-dir "$RUN_DIR" --start-all test_hybrid_hcdwf.ymmsl

Pure M3, No FoPla
------------------------

Use this pattern for the validated Pure M3 subset:

.. code-block:: text

   driver
     -> torbeam
     -> cyrano
     -> merge_waves
     -> hcd2core_sources

Pure benchmark yMMSL files follow the same structure:

.. code-block:: text

   driver <-> torbeam
   driver <-> cyrano
   driver <-> merge_waves
   driver <-> hcd2core_sources

Changing the Time Step
----------------------

Edit ``dt_required`` in ``input_workflow.xml``:

.. code-block:: xml

   <dt_required display="Time Step  [s]">20</dt_required>

For quick Pure validation, ``dt=20 s`` is useful. For runtime comparison, use
the same ``dt`` and same physics options across all modes.

Disabling Weighted Toroidal Modes
---------------------------------

For an apples-to-apples single-Cyrano comparison, set:

.. code-block:: yaml

   enabled: false
   modes: []

in ``ic_toroidal_modes.yaml``.
