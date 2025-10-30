Quick Start
===========

This guide will help you run your first HCD workflow simulation.

For Users (EasyBuild Module)
-----------------------------

Step 1: Load the Module
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   module load HCD-WF
   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

Step 2: Run a Test Case
~~~~~~~~~~~~~~~~~~~~~~~~

The HCD Workflow comes with test data. Try running the GRAYSCALE test:

.. code-block:: bash

   hcd_nogui -c /path/to/HCD-WF/tests/data/GRAYSCALE/

Step 3: View Results
~~~~~~~~~~~~~~~~~~~~~

The workflow will process the simulation and output results to the specified database.

For Developers (Python Environment)
------------------------------------

Step 1: Setup Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd hcd-wf
   source devenv/bin/activate
   
   # Load required modules
   module load Tkinter
   module load matplotlib
   module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   
   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

Step 2: Run Test Cases
~~~~~~~~~~~~~~~~~~~~~~~

**Console Mode (No GUI):**

.. code-block:: bash

   hcd_nogui -c tests/data/GRAYSCALE/

**Single Time Slice:**

.. code-block:: bash

   hcdslice_nogui -c tests/data/GRAYSCALE/

**Interactive GUI:**

.. code-block:: bash

   hcd_gui

**Batch Submission:**

.. code-block:: bash

   hcd_batch -n 1 -t 1 -e your.email@iter.org -q all -c tests/data/GRAYSCALE/

Understanding the Output
-------------------------

Console Output
~~~~~~~~~~~~~~

During execution, you'll see:

* Parameter loading messages
* Algorithm selection
* Process execution status
* Time slice information
* Completion messages

Example output:

.. code-block:: text

   path of the input workflow tests/data/GRAYSCALE/input_workflow.xml
   --- Default algorithm ---
   Algorithm = ['ec_wave_solver', 'fill_core_sources']
   ---------------------------------------------
   ---- Enter time loop of the H&CD wrapper ----
   Step = 1/1
   Time = 320.00 s
   dt   = 20.00 s
   Execute H&CD workflow for current time slice
   End of time slice
   End of wf_wrapper

Output Files
~~~~~~~~~~~~

Results are stored in IMAS database format according to your configuration in ``input_workflow.xml``.

Next Steps
----------

* Learn about :doc:`usage` for detailed command options
* See :doc:`examples` for more complex workflows
* Read :doc:`/reference/configuration` to customize your simulations
