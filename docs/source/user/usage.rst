Running and finding results
===========================

Once a case is saved, the :doc:`quickstart` and :doc:`execution_modes` pages
cover its launch. This page explains where the output goes and what to inspect
if a run stops.

Physics output
--------------

The output database is selected in ``input_workflow.xml`` by
``output_user_or_path``, ``output_database``, ``output_backend``,
``shot_nr`` and ``run_out``. Check these values before starting a new run.

The available output IDSs depend on the actors and post-processing selected.
Typical products are ``waves``, ``distributions``,
``distribution_sources`` and ``core_sources``. Open them with your IMAS
reader and check the stored time range before examining the profiles.
Use :doc:`validation` to distinguish successful execution from a result ready
for physics interpretation.

MUSCLE3 run files
-----------------

Hybrid and Pure launches create a directory under your configuration:

.. code-block:: text

   CONFIG/.hcd_gui_runs/<mode>_<unique-id>/
       configuration.ymmsl
       topology_source.txt
       ... MUSCLE3 instance logs and run files

``configuration.ymmsl`` records the paths actually used for that launch.
The selected source template is unchanged. These run files are separate from
the IMAS physics output.

The GUI also captures manager output in ``manager.log`` in that directory.
The command-line launcher prints manager output in the terminal.
Legacy prints workflow progress in the terminal and does not create a
MUSCLE3 run directory.

If a run stops
--------------

For a launch error, check the message first: a missing configuration file,
actor parameter file or mismatched Pure actor selection must be fixed before
MUSCLE3 starts.

For a running calculation, locate the failing actor's first error in the
terminal or instance log. Compare the generated topology with the saved
configuration, and confirm the actor was built for the loaded DD and runtime.
Repeated launches will not fix an input or actor-library mismatch.

Batch jobs
----------

Use :doc:`../reference/commands` for the existing ``hcd_batch`` interface
and its site-specific scheduler assumptions. For MUSCLE3 jobs, use a site
job script that prepares the environment and invokes the same
``run.sh MODE CONFIG`` command. The chosen topology controls actor resources.
