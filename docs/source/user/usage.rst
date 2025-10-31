Usage
=====

HCD Workflow provides four main commands for different use cases.

Commands Overview
-----------------

+-------------------+-----------------------------------------------------+
| Command           | Purpose                                             |
+===================+=====================================================+
| ``hcd_gui``       | Interactive graphical interface                     |
+-------------------+-----------------------------------------------------+
| ``hcd_nogui``     | Console-based workflow execution                    |
+-------------------+-----------------------------------------------------+
| ``hcdslice_nogui``| Single time slice execution                         |
+-------------------+-----------------------------------------------------+
| ``hcd_batch``     | Batch job submission for HPC clusters               |
+-------------------+-----------------------------------------------------+

hcd_gui - Graphical Interface
------------------------------

Launch the interactive GUI for workflow configuration and execution.

**Usage:**

.. code-block:: bash

   hcd_gui

**Features:**

* Visual workflow configuration
* Waveform editing with Waveform Cooker
* Real-time monitoring
* Interactive result visualization
* Machine description management

**When to Use:**

* Setting up new simulations
* Exploring parameter spaces
* Quick prototyping
* Educational purposes

hcd_nogui - Console Workflow
-----------------------------

Run the complete workflow from the command line without GUI.

**Usage:**

.. code-block:: bash

   hcd_nogui -c <configuration_folder>

**Arguments:**

* ``-c``, ``--config_folder``: Path to configuration folder containing ``input_workflow.xml`` (required)

**Example:**

.. code-block:: bash

   hcd_nogui -c tests/data/GRAYSCALE/

**When to Use:**

* Production runs
* Automated workflows
* Remote execution
* Time-loop simulations

**Output:**

The workflow will:

1. Load configuration from ``input_workflow.xml``
2. Initialize all actors and databases
3. Execute the time loop
4. Store results in output database

hcdslice_nogui - Single Time Slice
-----------------------------------

Execute the workflow for a single time slice.

**Usage:**

.. code-block:: bash

   hcdslice_nogui -c <configuration_folder>

**Arguments:**

* ``-c``, ``--config_folder``: Path to configuration folder (required)

**Example:**

.. code-block:: bash

   hcdslice_nogui -c tests/data/GRAYSCALE/

**When to Use:**

* Testing specific time points
* Debugging
* Quick validations
* Snapshot analysis

**Difference from hcd_nogui:**

* Executes only one time slice (no time loop)
* Faster for testing
* Useful for development

hcd_batch - Batch Execution
----------------------------

Submit workflow execution as a batch job to SLURM scheduler.

**Usage:**

.. code-block:: bash

   hcd_batch -n <nproc> -t <time> -e <email> -q <queue> -c <config_folder>

**Arguments:**

* ``-n``, ``--nproc``: Number of processors (required)
* ``-t``, ``--time``: Required CPU time in hours (required)
* ``-e``, ``--email``: Email for job status notifications (required)
* ``-q``, ``--queue``: SLURM partition/queue name (required)
* ``-c``, ``--config_folder``: Path to configuration folder (required)

**Example:**

.. code-block:: bash

   hcd_batch -n 1 -t 2 -e user@iter.org -q all -c tests/data/GRAYSCALE/

**Available Queues:**

Use ``sinfo`` to see available partitions on your cluster:

.. code-block:: bash

   sinfo

**Monitoring Jobs:**

Check job status:

.. code-block:: bash

   squeue -u $USER
   squeue -j <job_id>

View output:

.. code-block:: bash

   tail -f auto_batch_*.o<job_id>
   cat auto_batch_*.e<job_id>  # Errors

Cancel job:

.. code-block:: bash

   scancel <job_id>

**When to Use:**

* Long-running simulations
* Production workflows
* Resource-intensive calculations
* Unattended execution

Configuration Files
-------------------

input_workflow.xml
~~~~~~~~~~~~~~~~~~

The main configuration file that defines:

* Workflow parameters (shot, run, time range)
* Actor selection for each physics process
* Input/output database settings

Example structure:

.. code-block:: xml

   <root>
     <workflow_parameters>
       <shot_nr>130012</shot_nr>
       <run_in>5</run_in>
       <run_out>5</run_out>
       <tbegin>30.0</tbegin>
       <tend>350.0</tend>
       <dt_required>20</dt_required>
     </workflow_parameters>
     
     <actor_selection>
       <main_process>
         <ECRH>
           <ec_wave_solver list="genray gray grayscale torbeam toray">4</ec_wave_solver>
         </ECRH>
       </main_process>
     </actor_selection>
   </root>

See :doc:`/reference/configuration` for detailed options.

Waveform Files
~~~~~~~~~~~~~~

YAML files defining time-dependent heating parameters:

* ``ec_waveforms.yaml`` - ECRH waveforms
* ``ic_waveforms.yaml`` - ICRH waveforms
* ``nbi_waveforms.yaml`` - NBI waveforms
* ``lh_waveforms.yaml`` - LHCD waveforms

Best Practices
--------------

1. **Start with GUI**: Use ``hcd_gui`` to set up and validate configurations
2. **Test with Single Slice**: Use ``hcdslice_nogui`` for quick tests
3. **Use Console for Production**: Run ``hcd_nogui`` for production workflows
4. **Batch for Long Runs**: Use ``hcd_batch`` for multi-hour simulations
5. **Version Control**: Keep your configuration folders in git
6. **Document Settings**: Add comments to configuration files

Common Workflows
----------------

Interactive Development
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Setup
   module load HCD-WF
   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1
   
   # Configure and test
   hcd_gui
   
   # Run single slice to verify
   hcdslice_nogui -c my_config/
   
   # Run full workflow
   hcd_nogui -c my_config/

Production Batch Run
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Setup
   module load HCD-WF
   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1
   
   # Submit batch job
   hcd_batch -n 4 -t 8 -e user@iter.org -q all -c my_config/
   
   # Monitor
   squeue -u $USER
   watch -n 5 'squeue -u $USER'

Testing with Pytest
-------------------

You can run integration tests for the workflow using pytest. These tests execute the main workflow commands for various example configurations and check for successful completion.

**Install pytest (if not already installed):**

.. code-block:: bash

   pip install pytest

**Run all workflow tests:**

.. code-block:: bash

   pytest tests/test_workflow.py

Or run all tests in the directory:

.. code-block:: bash

   pytest tests/

The test file `tests/test_workflow.py` will run the workflow for several configurations and assert that each completes successfully.

Troubleshooting
---------------

Module Import Errors
~~~~~~~~~~~~~~~~~~~~~

Ensure all required modules are loaded:

.. code-block:: bash

   module list
   module load IMAS-AL-Python
   module load <actor_modules>

See Also
--------

* :doc:`/reference/commands` - Complete command reference
* :doc:`/reference/configuration` - Configuration file format
* :doc:`examples` - Example workflows
