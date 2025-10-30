Examples
========

This section provides practical examples for common HCD Workflow use cases.

Example 1: ECRH Simulation with GRAYSCALE
------------------------------------------

This example demonstrates running an Electron Cyclotron Resonance Heating (ECRH) simulation using the GRAYSCALE actor.

Configuration
~~~~~~~~~~~~~

Create or modify ``input_workflow.xml``:

.. code-block:: xml

   <root>
     <workflow_parameters>
       <input_user_or_path>public</input_user_or_path>
       <input_database>ITER</input_database>
       <input_backend>MDSPLUS</input_backend>
       <shot_nr>130012</shot_nr>
       <run_in>5</run_in>
       <output_user_or_path>default</output_user_or_path>
       <output_database>default</output_database>
       <output_backend>MDSPLUS</output_backend>
       <run_out>6</run_out>
       <tbegin>30.0</tbegin>
       <tend>350.0</tend>
       <dt_required>20</dt_required>
     </workflow_parameters>
     
     <actor_selection>
       <main_process>
         <ECRH>
           <ec_wave_solver list="genray gray grayscale torbeam toray">3</ec_wave_solver>
           <ec_wave_fp list="relax">0</ec_wave_fp>
         </ECRH>
       </main_process>
       
       <post_process>
         <source>
           <fill_core_sources list="hcd2core_sources">1</fill_core_sources>
         </source>
       </post_process>
     </actor_selection>
   </root>

Execution
~~~~~~~~~

**For Users (EasyBuild Module):**

.. code-block:: bash

   module load HCD-WF
   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1
   hcd_nogui -c my_ecrh_config/

**For Developers:**

.. code-block:: bash

   source devenv/bin/activate
   module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   hcd_nogui -c my_ecrh_config/

Example 2: Combined NBI + ICRH Simulation
------------------------------------------

Running both Neutral Beam Injection and Ion Cyclotron Resonance Heating.

Configuration
~~~~~~~~~~~~~

.. code-block:: xml

   <actor_selection>
     <main_process>
       <ICRH>
         <ic_coup list="iccoup">1</ic_coup>
         <ic_wave_solver list="cyrano tomcat pion lion">1</ic_wave_solver>
         <ic_wave_fp list="stixredist fopla">0</ic_wave_fp>
       </ICRH>
       
       <NBI>
         <nbi_source list="nemo bbnbi_serial bbnbi_parallel">1</nbi_source>
         <nbi_fp list="rabbit risk spot ascot_serial ascot_parallel nbisim">0</nbi_fp>
       </NBI>
     </main_process>
   </actor_selection>

Waveform Files
~~~~~~~~~~~~~~

Create ``ic_waveforms.yaml`` and ``nbi_waveforms.yaml`` in your configuration folder.

Execution
~~~~~~~~~

.. code-block:: bash

   module load HCD-WF
   hcd_nogui -c my_nbi_icrh_config/

Example 3: Batch Production Run
--------------------------------

Submit a long-running simulation to the cluster.

Setup
~~~~~

1. Prepare configuration folder with all necessary files
2. Test with single time slice first

.. code-block:: bash

   module load HCD-WF
   hcdslice_nogui -c production_run/

Batch Submission
~~~~~~~~~~~~~~~~

.. code-block:: bash

   hcd_batch -n 4 -t 12 -e user@iter.org -q all -c production_run/

Monitor Progress
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check job status
   squeue -u $USER
   
   # View output in real-time
   tail -f auto_batch_*.o<jobid>
   
   # Check for errors
   cat auto_batch_*.e<jobid>

Example 4: Interactive GUI Workflow
------------------------------------

Using the GUI for interactive analysis.

Launch GUI
~~~~~~~~~~

.. code-block:: bash

   module load HCD-WF
   hcd_gui

Workflow Steps
~~~~~~~~~~~~~~

1. **Load Configuration**: File → Open configuration folder
2. **Edit Waveforms**: Use Waveform Cooker integration
3. **Select Actors**: Choose appropriate physics codes
4. **Set Parameters**: Configure time range and step size
5. **Run**: Execute workflow
6. **Analyze**: View results and diagnostics

Example 5: Custom Actor Configuration
--------------------------------------

For developers testing new or modified actors.

Setup Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd hcd-wf
   source devenv/bin/activate
   
   # Install in editable mode
   pip install -e .
   
   # Load specific actor versions
   export ACTOR_FOLDER=~/development/actors
   export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH

Test Custom Actor
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   hcdslice_nogui -c test_config/

Example 6: Debugging Failed Runs
---------------------------------

Troubleshooting a simulation that fails.

Enable Verbose Output
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Don't suppress warnings
   unset IMAS_AL_DISABLE_OBSOLESCENT_WARNING
   
   # Run with output
   hcd_nogui -c problem_config/ 2>&1 | tee debug.log

Check Individual Components
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test just the time slice
   hcdslice_nogui -c problem_config/
   
   # Check configuration
   python -c "from hcdworkflow.workflow_config_reader import WorkflowConfigReader; \
              w = WorkflowConfigReader('problem_config/input_workflow.xml'); \
              import pprint; pprint.pprint(w.getWorkflowParameters())"

Run Static Analysis
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd hcd-wf
   source devenv/bin/activate
   pip install pylint black flake8
   
   # Check code quality
   pylint hcdworkflow/
   black --check hcdworkflow/
   flake8 hcdworkflow/

Example 8: Reproducible Research
---------------------------------

Ensuring reproducibility of simulation results.

Version Control
~~~~~~~~~~~~~~~

.. code-block:: bash

   cd my_project
   git init
   
   # Add configuration
   git add input_workflow.xml
   git add *.yaml
   
   # Document software versions
   module list > modules_used.txt
   pip freeze > requirements.txt
   
   git add modules_used.txt requirements.txt
   git commit -m "Initial simulation setup"

Documentation
~~~~~~~~~~~~~

Create a ``README.md`` in your configuration folder:

.. code-block:: markdown

   # Simulation: DT Baseline Scenario
   
   ## Purpose
   Evaluate ECRH performance for DT baseline
   
   ## Configuration
   - Shot: 130012
   - Run: 5
   - Time: 30-350s, dt=20s
   - Actors: GRAYSCALE (ECRH), HCD2CORE_SOURCES
   
   ## Execution
   ```bash
   module load HCD-WF/2.4.1
   hcd_nogui -c .
   ```
   
   ## Results
   Output in database: ITER/130012/6

Tips and Best Practices
------------------------

1. **Always Test First**: Use ``hcdslice_nogui`` before full runs
2. **Version Everything**: Use git for configurations
3. **Document Dependencies**: Record module versions
4. **Monitor Resources**: Check CPU/memory usage
5. **Backup Results**: Copy important outputs
6. **Use Batch for Long Runs**: Don't run multi-hour jobs interactively
7. **Check Logs**: Always review error logs after failures
8. **Validate Results**: Compare against known benchmarks

See Also
--------

* :doc:`usage` - Detailed usage instructions
* :doc:`/reference/configuration` - Configuration reference
* :doc:`../reference/actors` - Available actors and their options
