Hcd gui
=======

.. note::
   These instructions show how to execute the Python H&CD workflow from the GUI, where the input scenario, the physics actors, and a time loop can be defined. When running the H&CD workflow from a transport solver, the GUI is replaced by the transport code itself.


Open and Configure the H&CD Workflow
------------------------------------

To launch the GUI:

.. code-block:: bash

   hcd_gui

The main window appears with the default configuration.

.. figure:: /_static/gui_1.png
   :alt: HCD GUI main window
   :align: center

   HCD GUI main window after launch.

Workflow Parameters
-------------------

+----------------------------+------------------------------------------------+
| **Parameter**              | **Description**                                |
+----------------------------+------------------------------------------------+
| input_user_or_path         | User or absolute path of the input database.   |
|                            | `'public'` for the public database.            |
+----------------------------+------------------------------------------------+
| input_database             | Input database name (e.g., `'ITER'`).          |
+----------------------------+------------------------------------------------+
| input_shot / input_run     | Input shot and run numbers.                    |
+----------------------------+------------------------------------------------+
| output_user_or_path        | Output path or username (`$USER` if default).  |
+----------------------------+------------------------------------------------+
| output_database            | Output database (defaults to input database).  |
+----------------------------+------------------------------------------------+
| output_run                 | Output run number.                             |
+----------------------------+------------------------------------------------+
| start_time / end_time (s)  | Start and end time for H&CD calculation.       |
+----------------------------+------------------------------------------------+
| time_step (s)              | Time step for calculations (fixed currently).  |
+----------------------------+------------------------------------------------+
| parallel_workflow (0/1)    | Enable parallel execution (experimental).      |
+----------------------------+------------------------------------------------+
| single_time_slice (0/1)    | Run single time slice or full evolution.       |
+----------------------------+------------------------------------------------+

GUI Functions
-------------

- **Load** — Load configuration from a previous simulation.
- **Load Latest** — Load the most recent configuration.
- **Save / Save As** — Save the current configuration.
- **Run** — Save configuration and run the workflow.
- **Restore Default** — Restore default workflow parameters.

H&CD Processes
--------------

The right-hand side of the GUI allows selecting H&CD calculations:

- **ECRH** Select EC wave code for EC calculations.
- **ICRH** Select IC coupling, wave, and Fokker Planck codes.
- **NBI** Select beam deposition and Fokke Planck codes.
- **Nuclear** Codes for nuclear source and Fokker Planck calculations.
- **Sources / Profiles** Optionally fill `core_sources` and `core_profiles` IDS.


Edit Code Parameters
--------------------

Once H&CD actors are selected, click **Edit Code Parameters**.

Each actor (e.g., GRAY, NEMO, SPOT) opens a configuration window.  
Hover over a variable to see its definition. Invalid values highlight red.

- **Save** — saves configuration.  
- **Restore Default** — restores default input xsd definitions.

.. figure:: /_static/gui_2.png
   :alt: Edit Code Parameters window
   :align: center

   Edit Code Parameters window for an H&CD actor.

.. figure:: /_static/gui_3.png
   :alt: Example of parameter editing
   :align: center

   Example of editing parameters for a selected code.

Time Base
---------

Each process (ECRH, ICRH, NBI, Nuclear, etc.) can have its own
frequency of code calls per pulse phase.

**Modes:**

- *Full interval* — on/off for the full range.
- *Time step* — e.g., every 0.2 s.
- *At time* — trigger at a specific time slice.
- *Index step* — every N index steps.
- *At index* — trigger at a specific time step.

**Reset options:**

- *Soft reset* — erase extra-defined intervals.
- *Hard reset* — erase all intervals (used when workflow times are modified).

.. figure:: /_static/gui_6.png
   :alt: Example of waveform editing
   :align: center

   Example of editing H&CD waveforms in the GUI.

Edit H&CD Waveforms
-------------------

To simulate H&CD processes, you need:

#. **Input Scenario** — from the `Scenario Database` (e.g., ``equilibrium``, ``core_profiles``).
#. **Machine Geometry** — from the `Machine Description Database` (e.g., ``ec_launchers``, ``ic_antennas``, ``nbi``, ``lh_antennas``).
#. **Dynamic Configuration** — via the *Waveform Cooker* GUI, adding parameters like power, steering angle, or beam energy.

.. figure:: /_static/gui_4.png
   :alt: Waveform Cooker main window
   :align: center

   Waveform Cooker main window for dynamic configuration of H&CD parameters.

.. figure:: /_static/gui_5.jpg
   :alt: Editing a waveform parameter
   :align: center

   Example of editing a specific waveform parameter (e.g., power or steering angle).

Useful links:

- `Scenario Database <https://confluence.iter.org/spaces/IMP/pages/151422626/Scenario+Database>`_
- `Machine Description Database <https://confluence.iter.org/spaces/IMP/pages/302454631/Machine+Description+Database>`_


Execution
---------

Click **Run** in the GUI to start execution.  
Logs will appear in the console.

Example console output (truncated):

.. code-block:: none

  ---> Configuration saved in /home/ITER/schneim/public/git/hcd/data/nemo_spot_tuto
  -- Open input and output file
  ---- Enter time loop of the H&CD wrapper
  Step = 1 / 3
   Time = 300.00 s
   Execute H&CD workflow for current time slice
   -- Step 1: Source codes and Wave solvers
   -- NEMO NORMAL MODE
   START OF NEMO
   ...
   SPOT CPU consumption = 38.79 sec
   END OF SPOT
   End of H&CD workflow.
