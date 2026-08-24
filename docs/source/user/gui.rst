GUI
===

The GUI is useful for classic HCD Workflow configuration and quick inspection
of available workflow parameters. It is not the primary interface for current
Pure M3 yMMSL topology development.

Launch
------

.. code-block:: bash

   source config_hcd_iter_sdcc.sh
   hcd_gui

What the GUI Is Good For
------------------------

* Editing classic ``input_workflow.xml`` parameters.
* Selecting actors for the legacy iWrap workflow.
* Editing actor code parameters in the existing folder layout.
* Running or checking simple classic cases.

What It Does Not Replace
------------------------

Pure M3 mode needs an explicit yMMSL topology. The GUI does not currently
generate or validate those direct actor connections.

For Pure M3 work, edit the configuration folder and yMMSL file in the IDE, then
launch with:

.. code-block:: bash

   RUN_DIR=runs/pure_$(date +%Y%m%d_%H%M%S)
   mkdir -p "$RUN_DIR"
   muscle_manager --run-dir "$RUN_DIR" --start-all path/to/pure_case.ymmsl
