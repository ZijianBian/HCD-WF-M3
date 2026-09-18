Python entry points
===================

Most users should start with the :doc:`command-line tools
<../reference/commands>`. This page identifies the Python entry points and
modules useful when embedding or changing HCD-WF. The execution contracts
are described in :doc:`architecture`.

Running a configured workflow
-----------------------------

``workflow.workflow_driver.workflow_driver(par_path, m3_flag=0)`` opens the
databases, runs the configured time loop and closes the databases on exit.
``par_path`` is a directory containing ``input_workflow.xml``. The default
``m3_flag=0`` runs Legacy in the current process. ``m3_flag=1`` starts the
Hybrid macro and requires a MUSCLE3 Manager connection.

``workflow.wf_wrapper.wf_wrapper`` remains an alias for this entry point
for older callers. New integrations should use ``workflow_driver``.
The Hybrid micro and Pure driver expose ``main()`` in
``hcdworkflow.hcd_workflow_m3`` and
``hcdworkflow.workflow_driver_m3_pure`` respectively; topology templates
launch these as MUSCLE3 components.

Computing one slice
-------------------

``hcdworkflow.hcd_workflow.HCDWorkflow`` provides the in-process actor
chain used by Legacy and Hybrid:

.. code-block:: python

   from hcdworkflow.hcd_workflow import HCDWorkflow

   hcd = HCDWorkflow()
   hcd.initialize(config_directory)
   hcd.setProcessStatus(timestamp)
   outputs = hcd.run(
       equilibrium=equilibrium,
       core_profiles=core_profiles,
       workflow=workflow_ids,
       **other_input_ids,
   )

The caller supplies prepared IMAS IDS objects and handles storage. The
return value is a dictionary keyed by output IDS name; it can be ``None``
when actor execution reports an error. ``finalize()``, ``get_state()``,
``set_state()`` and ``get_timestamp()`` are currently placeholders, so they
do not provide checkpointing or actor cleanup.

Where to make a change
----------------------

.. list-table::
   :header-rows: 1

   * - Module
     - Responsibility
   * - ``gui.launch_config``
     - ``materialize_ymmsl()`` binds and validates a topology;
       ``prepare_muscle_launch()`` creates its run directory;
       ``launch_muscle()`` starts Manager and returns the plan and process.
   * - ``workflow.workflow_driver``
     - ``setup_databases()``, ``resolve_time_range()``,
       ``get_ids_slices()`` and ``store_ids_slices()`` support the drivers.
   * - ``workflow.ids_prep``
     - IDS conversion, waveform preparation and stable output structures.
   * - ``hcdworkflow.workflow_config_reader``
     - ``WorkflowConfigReader`` parses the workflow XML and actor selection.
   * - ``hcdworkflow.workflow_data``
     - ``WorkflowData`` builds actor and process state from a configuration.
   * - ``hcdworkflow.workflow_executor``
     - ``WorkflowExecutor`` chooses and executes the in-process algorithm.
   * - ``hcdworkflow.workflow_actor``
     - ``WorkflowActor`` loads iWrap actors and their IDS interfaces.
   * - ``hcdworkflow.workflow_dbhelper``
     - ``WorkflowDbHelper`` opens IMAS databases. Its ``ddv_backend``
       argument is required; callers supply the intended DD version.

These modules are the implementation map, not a promise that every helper
is a stable external API. Check the source signature when building an
integration, particularly for functions whose names begin with ``_``.
