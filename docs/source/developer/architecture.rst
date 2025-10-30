Architecture
============

This document describes the architecture and design of the HCD Workflow system.

System Overview
---------------

The HCD Workflow is built on a modular architecture that separates:

1. **Workflow Management** - Orchestration logic
2. **Actor System** - Physics code interfaces
3. **Data Management** - IMAS database operations
4. **User Interface** - GUI and CLI components

Component Diagram
-----------------

::

    ┌─────────────────────────────────────────────────────┐
    │          User Interface Layer                       │
    │  ┌──────────┐  ┌──────────┐  ┌───────────────┐    │
    │  │ hcd_gui  │  │hcd_nogui │  │  hcd_batch    │    │
    │  └──────────┘  └──────────┘  └───────────────┘    │
    └─────────────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────────────┐
    │        Workflow Driver Layer                        │
    │  ┌─────────────────────────────────────┐           │
    │  │   WorkflowDriver                    │           │
    │  │   - executeTimeloop()               │           │
    │  │   - getIDSSlices()                  │           │
    │  │   - storeIDSSlices()                │           │
    │  └─────────────────────────────────────┘           │
    └─────────────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────────────┐
    │        Workflow Execution Layer                     │
    │  ┌─────────────────────────────────────┐           │
    │  │   WorkflowExecutor                  │           │
    │  │   - decideAlgorithm()               │           │
    │  │   - adjustAlgorithm()               │           │
    │  │   - executeAlgorithm()              │           │
    │  └─────────────────────────────────────┘           │
    └─────────────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────────────┐
    │        Actor Layer                                  │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
    │  │GRAYSCALE │ │  CYRANO  │ │   NEMO   │  ...      │
    │  └──────────┘ └──────────┘ └──────────┘           │
    └─────────────────────────────────────────────────────┘
                           ↓
    ┌─────────────────────────────────────────────────────┐
    │        Data Layer                                   │
    │  ┌─────────────────────────────────────┐           │
    │  │   IMAS Database                     │           │
    │  │   - Input DB                        │           │
    │  │   - Output DB                       │           │
    │  │   - Machine Description DB          │           │
    │  └─────────────────────────────────────┘           │
    └─────────────────────────────────────────────────────┘

Core Components
---------------

hcdworkflow Package
~~~~~~~~~~~~~~~~~~~

The main workflow package contains:

**hcd_workflow.py**
  Main workflow orchestration class. Coordinates actor execution.

**workflow_driver.py**
  Implements time-loop execution, IDS slice management, and output storage.

**workflow_executor.py**
  Manages actor execution sequence, dependencies, and parallel execution.

**workflow_data.py**
  Handles workflow configuration data and validation.

**workflow_config_reader.py**
  Parses XML configuration files and extracts parameters.

**workflow_dbhelper.py**
  IMAS database operations and connections.

**workflow_globals_reader.py**
  Reads global configuration (algorithms, dependencies, presets).

**workflow_actor.py**
  Actor wrapper and interface definition.

Workflow Execution Flow
------------------------

1. **Initialization**
   
   .. code-block:: python

      # Load configuration
      workflowConfig = WorkflowConfigReader(xml_file)
      workflowData = WorkflowData(config_folder)
      
      # Setup databases
      dbhelper = WorkflowDbHelper(...)
      inputDb = dbhelper.getInputDatabase()
      outputDb = dbhelper.getOutputDatabase()

2. **Time Loop**
   
   .. code-block:: python

      for time_slice in time_range:
          # Get IDS slices at current time
          idsSlices = getIDSSlices(timenow)
          
          # Execute workflow
          idsData = workflow.run(**idsSlices)
          
          # Store results
          storeIDSSlices(idsData)

3. **Algorithm Decision**
   
   .. code-block:: python

      # Choose algorithm based on configuration
      if ic_wave_fp == "fopla":
          algorithm = "nbi_ic_synergy"
      else:
          algorithm = "default"

4. **Actor Execution**
   
   .. code-block:: python

      for process in algorithm:
          # Get selected actor
          actor = dictionary_of_actors[process]
          
          # Execute
          result = actor(*input_ids)
          
          # Handle mergers if needed
          if multiple_outputs:
              result = merge_actor(results)

Data Flow
---------

Input Data
~~~~~~~~~~

1. **Scenario Data** (equilibrium, core_profiles, workflow)
   
   * Read from input database
   * Sliced at each time point

2. **Machine Description** (NBI, IC antennas, EC launchers, wall)
   
   * Static or slowly varying
   * Loaded from machine database

3. **Configuration**
   
   * XML files for workflow parameters
   * YAML files for waveforms
   * Actor-specific parameter files

Processing
~~~~~~~~~~

1. **Actor Execution**
   
   * Each actor receives required input IDSs
   * Performs physics calculations
   * Returns output IDSs

2. **Merging**
   
   * Multiple actors may produce same IDS type
   * Merger actors combine results
   * Handle overlapping time ranges

Output Data
~~~~~~~~~~~

1. **Process Outputs**
   
   * waves, distributions, distribution_sources
   * Stored slice-by-slice

2. **Derived Data**
   
   * core_sources (power deposition)
   * core_profiles (updated)
   * Stored to output database

Actor System
------------

Actor Interface
~~~~~~~~~~~~~~~

All actors must implement:

.. code-block:: python

    def actor_function(*input_ids) -> output_ids:
        """
        Process input IDSs and return output.
        
        Args:
            *input_ids: Variable number of IMAS IDS objects
            
        Returns:
            output_ids: Single IDS or list of IDSs
        """
        pass

Actor Categories
~~~~~~~~~~~~~~~~

**Wave Solvers**
  * ec_wave_solver: GRAYSCALE, GRAY, TORBEAM, TORAY
  * ic_wave_solver: CYRANO, TOMCAT, PION, LION
  * lh_wave_solver: LHCD-METIS

**Source Codes**
  * nbi_source: NEMO, BBNBI
  * nuclear_source: AFSI

**Fokker-Planck**
  * ec_wave_fp: RELAX
  * ic_wave_fp: STIXREDIST, FOPLA
  * nbi_fp: ASCOT, RISK, SPOT, NBISIM

**Post-Processing**
  * fill_core_sources: HCD2CORE_SOURCES
  * fill_core_profiles: HCD2CORE_PROFILES

**Mergers**
  * merge_waves
  * merge_distributions
  * merge_distribution_sources
  * merge_core_sources

Actor Dependencies
~~~~~~~~~~~~~~~~~~

Defined in ``global_lists.yaml``:

.. code-block:: yaml

    prerequisites:
      ec_wave_fp:
        relax:
          ec_wave_solver: any
      ic_wave_fp:
        fopla:
          ic_wave_solver: any
          nbi_source: any
          nbi_fp: any

Configuration System
--------------------

Hierarchy
~~~~~~~~~

1. **Global Configuration** (``global_lists.yaml``)
   
   * Algorithms
   * Actor lists
   * Dependencies
   * Parallel execution rules

2. **Workflow Configuration** (``input_workflow.xml``)
   
   * Workflow parameters
   * Actor selection
   * Time range

3. **Actor Configuration** (``input_<actor>.xml``)
   
   * Actor-specific parameters
   * Per-process configuration

4. **Waveforms** (``*_waveforms.yaml``)
   
   * Time-dependent parameters
   * Power, position, etc.

Configuration Loading
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Global lists
    globalListReader = WorkflowGlobalsReader(yaml_file)
    algorithms = globalListReader.getAlgorithms()
    
    # Workflow config
    workflowConfig = WorkflowConfigReader(xml_file)
    param_process = workflowConfig.getParamProcess()
    
    # Waveforms
    idsObject = add_dynamic(yaml_file)

Parallel Execution
------------------

Dependency Graph
~~~~~~~~~~~~~~~~

The workflow analyzes dependencies to enable parallel execution:

.. code-block:: python

    parallel_dependency:
      ec_wave_solver: None  # Can run first
      lh_wave_solver: None  # Can run in parallel with EC
      ic_wave_solver: [ic_coup, nbi_source, nbi_fp]  # Depends on these

Execution Strategy
~~~~~~~~~~~~~~~~~~

1. **Independent actors** run in parallel
2. **Dependent actors** wait for prerequisites
3. **Mergers** run after all contributing actors

Example:

::

    Parallel Step 0: [ec_wave_solver, lh_wave_solver, nbi_source]
    Parallel Step 1: [nbi_fp]
    Parallel Step 2: [ic_coup]
    Parallel Step 3: [ic_wave_solver]
    Parallel Step 4: [merge_waves, fill_core_sources]

Error Handling
--------------

Validation
~~~~~~~~~~

* Configuration validation at startup
* Actor prerequisite checking
* IDS consistency checks

Error Recovery
~~~~~~~~~~~~~~

* Continue execution if optional processes fail
* Skip disabled processes gracefully
* Detailed error logging

GUI Architecture
----------------

Component Structure
~~~~~~~~~~~~~~~~~~~

**gui_methods.py**
  Core GUI operations, XML handling, loading/saving

**waveform_edition.py**
  Waveform editor integration

**time_base_edition.py**
  Time parameter editing

**tooltip.py**
  UI tooltip system

GUI Integration
~~~~~~~~~~~~~~~

.. code-block:: python

    # GUI creates configuration
    workflow_param = create_workflow_param_from_file(xml)
    
    # Launches workflow
    wf_wrapper(config_folder)

Design Patterns
---------------

Strategy Pattern
~~~~~~~~~~~~~~~~

Algorithm selection based on configuration:

.. code-block:: python

    if condition:
        algorithm = self.algorithm["default"]
    else:
        algorithm = self.algorithm["nbi_ic_synergy"]

Factory Pattern
~~~~~~~~~~~~~~~

Actor creation from configuration:

.. code-block:: python

    actor = WorkflowActor.getObject(actor_name)

Observer Pattern
~~~~~~~~~~~~~~~~

Status updates and progress monitoring (in GUI)

Extensibility
-------------

Adding New Actors
~~~~~~~~~~~~~~~~~

1. Create actor wrapper following interface
2. Add to ``global_lists.yaml``
3. Add configuration template
4. Define dependencies
5. Test integration

Adding New Algorithms
~~~~~~~~~~~~~~~~~~~~~

1. Define sequence in ``global_lists.yaml``
2. Specify dependencies
3. Test with various configurations

Performance Considerations
--------------------------

* **Lazy Loading**: IDSs loaded only when needed
* **Parallel Execution**: Independent actors run concurrently
* **Memory Management**: IDSs released after use
* **Database Optimization**: Slice-based access

Best Practices
--------------

Code Organization
~~~~~~~~~~~~~~~~~

* Keep workflow logic separate from physics
* Use type hints for clarity
* Document complex algorithms
* Follow PEP 8 style guide

Testing
~~~~~~~

* Test with provided test data
* Validate against known results
* Check edge cases
* Test parallel execution

Documentation
~~~~~~~~~~~~~

* Document all public interfaces
* Explain complex algorithms
* Provide usage examples
* Keep docs in sync with code

See Also
--------

* :doc:`contributing` - How to contribute
* :doc:`api` - API reference
* :doc:`setup` - Development setup
