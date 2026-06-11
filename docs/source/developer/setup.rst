Developer Setup
===============

Use the project helper unless you are deliberately reproducing an old stack.

Current Stack
-------------

.. code-block:: bash

   source config_hcd_iter_sdcc.sh

This prepares the current DD 4.1.0 and MUSCLE3 development environment.

Legacy Stack
------------

.. code-block:: bash

   source config_hcd_iter_sdcc_3.42.0.sh

Use this for old DD 3.42.0 compatibility cases only.

Useful Checks
-------------

.. code-block:: bash

   which python
   python -c "import imas; print(imas.__file__)"
   python -c "import libmuscle; print('MUSCLE3 ok')"
   module list

Run Python Checks
-----------------

.. code-block:: bash

   python3 -m py_compile workflow/workflow_driver.py workflow/ids_prep.py hcdworkflow/workflow_driver_m3_pure.py
   pytest tests/test_ids_prep.py

Full workflow runs require the SDCC actor environment and valid IMAS input
runs.

Build the Docs
--------------

.. code-block:: bash

   ./devenv/bin/python -m pip install -e ".[docs]"
   cd docs
   ../devenv/bin/python -m sphinx -M html source build

Code Map
--------

.. list-table::
   :header-rows: 1

   * - Path
     - Purpose
   * - ``workflow/workflow_driver.py``
     - Legacy driver and Hybrid M3 macro.
   * - ``hcdworkflow/hcd_workflow_m3.py``
     - Hybrid M3 micro that calls ``HCDWorkflow.run()``.
   * - ``hcdworkflow/workflow_driver_m3_pure.py``
     - Pure M3 actor macro driver.
   * - ``workflow/ids_prep.py``
     - IDS fix-ups, waveform helpers, and IC toroidal mode helpers.
   * - ``hcdworkflow/hcd_workflow.py``
     - Classic workflow orchestration.
   * - ``hcdworkflow/workflow_executor.py``
     - Actor selection and execution.
