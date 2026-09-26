Quickstart
==========

For a first run, use a configuration and input database that you can already
read. A configuration folder contains ``input_workflow.xml``, actor parameter
files, and any waveform files. If you need to create one, follow :doc:`gui`.
The workflow does not download a plasma scenario for you.

Prepare the environment
-----------------------

After the one-time :doc:`installation`, open a shell in the repository root:

.. code-block:: bash

   export ACTOR_FOLDER=/path/to/PYTHON_ACTORS
   source config_hcd_iter_sdcc.sh

Replace the actor path with your installed DD 4.1.0 actors. The helper prepares
the environment; it does not build the actors.

Check the case and run
----------------------

In your saved ``input_workflow.xml``, check the input database, selected
actors and time range. Choose an output location and ``run_out`` intended for
this calculation: starting a run creates the configured output database.

Start with Legacy mode if your case uses iWrap actors:

.. code-block:: bash

   ./run.sh legacy /path/to/config

For MUSCLE3, choose a matching configuration and topology as described in
:doc:`execution_modes`. Replacing ``legacy`` with ``pure`` also changes the
actor executable requirements.

Read the result
---------------

The terminal shows the current time slice and actor messages. Physics results
are written to the IMAS database selected by the configuration.
For MUSCLE3 runs, the launcher also prints the run-directory path.

Open the output with your IMAS reader and check that the expected times and
heating sources are present. See :doc:`usage` for file locations and
:doc:`validation` for the checks to make before interpreting a result.
