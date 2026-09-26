Preparing a case in the GUI
===========================

Launch ``hcd_gui`` from the configured shell. It opens the default workflow;
use **Load** to open a saved configuration.

The GUI needs the selected actors' iWrap Python packages to edit parameters
and save a case, including for Pure launches. If you have only native MUSCLE3
executables, use ``run.sh pure`` with an already prepared configuration.

Set the workflow and actors
---------------------------

In **Workflow parameters**, choose the input database, shot and run. Set the
output location, time range and time step. The exact XML field names are in
:doc:`../reference/configuration`.

In **Actor selection**, choose the codes for the heating systems you need,
then select the source or profile post-processing. Only use actors installed
for your current environment.

Use **Save as** to create a configuration folder, or **Save** to update it.
Keep this folder at a location you can reuse from the command line.

Edit actor parameters and waveforms
-----------------------------------

**Edit Code Parameters** opens the selected actors' parameter editors.
Check and save each actor's settings before running the case.

.. figure:: /_static/gui_2.png
   :alt: Actor parameter editor with Save and Restore default controls
   :width: 75%

   The actor parameter editor. Its fields depend on the installed actor.

**Edit H&CD waveforms** opens Waveform Cooker for time-dependent inputs such
as power, steering or beam energy. The scenario supplies the plasma state;
the heating geometry and waveform settings supply the actuator inputs.
Legacy and Hybrid also expose **Time Base** controls for individual process
schedules. Pure uses its own scheduling rules; see
:doc:`../developer/architecture`.

Choose how to launch
--------------------

The **Execution / Launch** panel offers Legacy, Hybrid and Pure.
Legacy is selected whenever the GUI starts. For Hybrid or Pure, select the
matching yMMSL template; **Use recommended topology** restores the mode's
default template.

Pure includes only the selected actors in the generated run configuration.
Launch checks their connections and parameter files. See :doc:`execution_modes`
for supported actors and requirements.

Click **Save & Run** to save the case and start the selected mode. A MUSCLE3
launch reports the generated topology and manager log path. Follow that log
and open the output database to inspect the result; see :doc:`usage`.

The GUI edits the configuration and starts the workflow. It does not provide
a physics-results viewer. The launch mode and topology choice are separate
from ``input_workflow.xml``, so select them again after reopening the GUI.
