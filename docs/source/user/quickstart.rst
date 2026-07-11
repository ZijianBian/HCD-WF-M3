Quickstart
==========

This page is the shortest path to a useful run on ITER SDCC.

Prepare the Environment
-----------------------

From the repository root:

.. code-block:: bash

   source config_hcd_iter_sdcc.sh

This helper prepares the DD 4.1.0 development stack, MUSCLE3, iWrap paths,
Waveform Cooker paths, and the local ``devenv`` environment used by the current
M3 work.

Use ``config_hcd_iter_sdcc_3.42.0.sh`` only when you intentionally need the
legacy DD 3.42.0 stack.

Run a Legacy Smoke Case
-----------------------

Legacy mode runs the full workflow in one Python process. It is the baseline
for comparing M3 behavior.

.. code-block:: bash

   python workflow/workflow_driver.py tests/m3_hybrid 0

The final line should include:

.. code-block:: text

   [workflow_driver] Workflow completed successfully

Run a Hybrid M3 Case
--------------------

Hybrid mode uses MUSCLE3 for the driver-to-workflow boundary:

.. code-block:: bash

   muscle_manager --start-all hcdwf_hybrid_m3.ymmsl

The topology is:

.. code-block:: text

   workflow_driver.py  <->  hcd_workflow_m3.py  ->  iWrap actors

Run a Pure M3 Case
-------------------------------

Pure mode can be launched either through ``run.sh pure`` or directly through
MUSCLE3. The runner defaults to the maintained no-Rabbit actor-level topology:

.. code-block:: bash

   ./run.sh pure

The equivalent direct MUSCLE3 command is:

.. code-block:: bash

   muscle_manager --start-all hcdwf_pure_m3.ymmsl

The Pure topology is:

.. code-block:: text

   driver -> torbeam_m3.exe -> waves_ec
   driver -> cyrano_m3.exe  -> waves_ic
   driver -> merge_waves_m3.exe -> waves
   driver -> hcd2core_sources_m3.exe -> core_sources

Pure mode supports EC-only, IC-only, and combined runs. It skips inactive
branches without manufacturing the other branch or reordering actor output.

Run Pure M3 with Rabbit
-----------------------

Rabbit requires the external GCC actor and a local, user-provided NBI case:

.. code-block:: text

   $ACTOR_FOLDER/rabbit/rabbit_m3.exe
   tests/m3_pure_rabbit/input_workflow.xml
   tests/m3_pure_rabbit/nbi_waveforms.yaml
   tests/m3_pure_rabbit/NBI/nbi_fp/input_rabbit.xml

After preparing those files:

.. code-block:: bash

   ./run.sh pure-rabbit

The main shell remains on the Intel HCD stack; Rabbit switches to its GCC/foss
runtime inside a separate child process.

Inspect Results
---------------

Output is written to the IMAS run specified by ``input_workflow.xml``. Use the
configured database, backend, shot, and output run when inspecting results with
IMAS-Python or SDCC tools such as IDStools.

Next Pages
----------

* :doc:`execution_modes` explains the execution modes.
* :doc:`validation` records what has been tested.
* :doc:`../developer/troubleshooting` lists common failure modes.
