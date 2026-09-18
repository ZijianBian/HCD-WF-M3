Command reference
=================

Run these commands in the environment described in :doc:`../user/installation`.
``CONFIG_DIRECTORY`` is a saved configuration containing ``input_workflow.xml``
and the selected actors' parameter files.

Source-checkout launcher
------------------------

.. code-block:: bash

   ./run.sh legacy /path/to/config
   ./run.sh hybrid /path/to/config [TOPOLOGY.ymmsl]
   ./run.sh pure /path/to/config [TOPOLOGY.ymmsl]

``./run.sh --help`` prints usage. Legacy takes no topology argument. Hybrid and
Pure choose the topology in this order: the command-line argument,
``HCD_HYBRID_YMMSL`` or ``HCD_PURE_YMMSL``, then ``topologies/hybrid.ymmsl`` or
``topologies/pure.ymmsl``. See :doc:`../user/execution_modes` for actor choices.

The launcher creates a run directory under ``CONFIG_DIRECTORY/.hcd_gui_runs/``
and runs MUSCLE3 Manager in the foreground. Manager output appears in the
terminal; component logs and the generated topology are in that run directory.
Physics outputs go to the IMAS output entry specified in the configuration.

Installed commands
------------------

``hcd_gui``
   Opens the configuration editor. It takes no command-line options. Save & Run
   launches the selected execution mode; MUSCLE3 runs also capture Manager
   output in ``manager.log`` inside the displayed run directory.

``hcd_nogui -c /path/to/config [--m3_flag 0|1]``
   Runs the time-loop driver. ``-c`` and ``--config_folder`` are equivalent.
   ``--m3_flag`` defaults to ``0`` (Legacy); ``1`` is the Hybrid macro component
   and needs a running MUSCLE3 configuration. Use ``run.sh hybrid`` to launch
   both Hybrid components together. This command does not select Pure mode.

``hcdslice_nogui -c /path/to/config``
   Older single-slice entry point; its only option is ``-c`` / ``--config_folder``.
   It currently fixes the time at **320 s** and does not store the returned
   workflow outputs. For a configurable slice with normal output storage, set
   ``one_time_slice`` to ``1`` in the XML and use ``hcd_nogui`` or ``run.sh``.

Batch wrapper
-------------

``hcd_batch`` requires all five arguments:

.. list-table::
   :header-rows: 1

   * - Argument
     - Meaning
   * - ``-n``, ``--nproc``
     - Tasks per node
   * - ``-t``, ``--time``
     - Requested wall time in hours
   * - ``-e``, ``--email``
     - Address for the end-of-job notification
   * - ``-q``, ``--queue``
     - Queue / partition name
   * - ``-c``, ``--config_folder``
     - Saved configuration directory

It writes ``auto_batch_<timestamp>`` in the current directory and submits a
Legacy ``hcd_nogui`` run. The wrapper writes ``#SBATCH`` directives but calls
``qsub``; it therefore depends on the site's submission setup. It is not a
general SLURM or MUSCLE3 launcher.

Python entry points
-------------------

``python3 workflow/workflow_driver.py /path/to/config [0|1]`` uses the same
Legacy / Hybrid flag as ``hcd_nogui``. ``workflow/wf_wrapper.py`` remains a
compatibility entry point with the same arguments. Pure runs use
``hcdworkflow/workflow_driver_m3_pure.py`` through their yMMSL topology.
