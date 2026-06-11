Command Reference
=================

Environment
-----------

.. code-block:: bash

   source config_hcd_iter_sdcc.sh

Build documentation:

.. code-block:: bash

   cd docs
   ../devenv/bin/python -m sphinx -M html source build

Classic Commands
----------------

.. list-table::
   :header-rows: 1

   * - Command
     - Purpose
   * - ``hcd_gui``
     - Open the classic GUI.
   * - ``hcd_nogui -c CONFIG``
     - Run the classic console workflow.
   * - ``hcdslice_nogui -c CONFIG``
     - Run one classic time slice.
   * - ``hcd_batch -c CONFIG``
     - Submit a classic batch job.

Driver Commands
---------------

Legacy:

.. code-block:: bash

   python workflow/workflow_driver.py CONFIG 0

Hybrid macro, normally launched by MUSCLE3:

.. code-block:: bash

   python workflow/workflow_driver.py CONFIG 1

Pure M3 driver, normally launched by MUSCLE3:

.. code-block:: bash

   python hcdworkflow/workflow_driver_m3_pure.py CONFIG

MUSCLE3
-------

.. code-block:: bash

   muscle_manager --start-all FILE.ymmsl

Inspecting IDS Data
-------------------

Use the database, backend, shot, and run from ``input_workflow.xml``. On SDCC,
prefer stable IMAS tooling such as IDStools or IMAS-Python scripts for IDS
inspection.

.. code-block:: bash

   module avail IDStools
