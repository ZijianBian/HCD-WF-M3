Command Line Reference
======================

HCD Workflow provides four main commands for different use cases.

hcd_gui
-------

Interactive graphical user interface for workflow configuration and execution.

**Usage:**

.. code-block:: bash

   hcd_gui [options]

**Description:**

Launches a GUI application that allows you to:

* Configure workflow parameters interactively
* Edit waveforms visually
* Set up time evolution parameters
* Select and configure actors
* Run simulations with real-time monitoring
* View results and logs

**Options:**

Currently accepts no command-line options. All configuration is done through the GUI.

**Example:**

.. code-block:: bash

   # Launch GUI
   hcd_gui

hcd_nogui
---------

Console-based workflow execution with time-loop support.

**Usage:**

.. code-block:: bash

   hcd_nogui -c <configuration_folder> [options]

**Description:**

Executes the complete workflow in console mode, processing all time slices sequentially.

**Required Arguments:**

``-c``, ``--config <path>``
   Path to the configuration folder containing workflow XML files and input data.

**Optional Arguments:**

``--verbose``
   Enable verbose output for debugging.

``--log <file>``
   Write output to specified log file.

**Examples:**

.. code-block:: bash

   # Basic execution
   hcd_nogui -c tests/data/GRAYSCALE/
   
   # With verbose output
   hcd_nogui -c my_simulation/ --verbose
   
   # Save logs to file
   hcd_nogui -c my_simulation/ --log output.log

hcdslice_nogui
--------------

Execute workflow for a single time slice.

**Usage:**

.. code-block:: bash

   hcdslice_nogui -c <configuration_folder> [options]

**Description:**

Runs the workflow for a single time point. Useful for:

* Testing actor configurations
* Debugging workflow issues
* Quick validation of setup
* Development and testing

**Required Arguments:**

``-c``, ``--config <path>``
   Path to the configuration folder containing workflow XML files.

**Optional Arguments:**

``--time <value>``
   Specific time point to execute (default: first time in configuration).

``--verbose``
   Enable verbose output.

**Examples:**

.. code-block:: bash

   # Execute single slice
   hcdslice_nogui -c tests/data/GRAYSCALE/
   
   # Specific time point
   hcdslice_nogui -c my_simulation/ --time 50.0
   
   # Verbose mode
   hcdslice_nogui -c my_simulation/ --verbose

hcd_batch
---------

Submit workflow as SLURM batch job.

**Usage:**

.. code-block:: bash

   hcd_batch -c <configuration_folder> [options]

**Description:**

Submits the workflow to SLURM scheduler for execution on HPC cluster. Automatically generates batch script and submits job.

**Required Arguments:**

``-c``, ``--config <path>``
   Path to the configuration folder.

**Optional Arguments:**

``--partition <name>``
   SLURM partition to use (default: all).

``--nodes <n>``
   Number of nodes to request (default: 1).

``--ntasks <n>``
   Number of tasks (default: 1).

``--time <hh:mm:ss>``
   Wall time limit (default: 01:00:00).

``--job-name <name>``
   Job name for SLURM (default: hcd_workflow).

``--mail-user <email>``
   Email for job notifications.

``--mail-type <types>``
   When to send email (BEGIN,END,FAIL,ALL).

**Available Partitions:**

* ``all`` - General partition (default)
* ``sun`` - Sun nodes
* ``vega`` - Vega nodes
* ``sirius`` - Sirius nodes
* ``rigel`` - Rigel nodes
* ``titan`` - Titan nodes
* ``*_debug`` - Debug versions of above

**Examples:**

.. code-block:: bash

   # Basic batch submission
   hcd_batch -c my_simulation/
   
   # Specify partition and time
   hcd_batch -c my_simulation/ --partition sun --time 02:00:00
   
   # With email notifications
   hcd_batch -c my_simulation/ --mail-user user@iter.org --mail-type END,FAIL
   
   # Custom job name
   hcd_batch -c my_simulation/ --job-name my_hcd_run

**Monitoring Jobs:**

.. code-block:: bash

   # Check job status
   squeue -u $USER
   
   # View job details
   scontrol show job <job_id>
   
   # Cancel job
   scancel <job_id>

Common Options
--------------

Configuration Folder Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All commands expect a configuration folder with:

.. code-block:: text

   configuration_folder/
   ├── input_workflow.xml          # Main workflow configuration
   ├── global_lists.yaml           # Global parameters (optional)
   ├── waveforms/                  # Waveform files (if used)
   └── input_data/                 # Input IDS files

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

``IMAS_AL_DISABLE_OBSOLESCENT_WARNING``
   Set to ``1`` to suppress IMAS warning messages.

.. code-block:: bash

   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

Exit Codes
~~~~~~~~~~

* ``0`` - Success
* ``1`` - Configuration error
* ``2`` - Execution error
* ``3`` - Actor error

See Also
--------

* :doc:`../user/usage` - Usage guide with examples
* :doc:`../user/examples` - Example workflows
* :doc:`configuration` - Configuration file format
