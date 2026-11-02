Configuration Reference
=======================

This page describes the configuration file formats used by HCD Workflow.

Workflow Configuration (XML)
-----------------------------

The main workflow configuration is defined in ``input_workflow.xml``.

File Structure
~~~~~~~~~~~~~~

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8"?>
   <workflow>
       <workflow_parameters>
           <!-- Workflow-level settings -->
       </workflow_parameters>
       
       <actors>
           <!-- Actor configurations -->
       </actors>
       
       <time_evolution>
           <!-- Time loop settings -->
       </time_evolution>
   </workflow>

Workflow Parameters
~~~~~~~~~~~~~~~~~~~

Global workflow settings:

.. code-block:: xml

   <workflow_parameters>
       <shot>123456</shot>
       <run>1</run>
       <user>username</user>
       <database>iterdb</database>
       <version>3</version>
       <verbose>true</verbose>
   </workflow_parameters>

**Parameters:**

* ``shot`` - Shot number for IDS
* ``run`` - Run number for IDS
* ``user`` - Username for IDS access
* ``database`` - Database name (e.g., iterdb)
* ``version`` - IDS version
* ``verbose`` - Enable verbose logging (true/false)

Actor Configuration
~~~~~~~~~~~~~~~~~~~

Each actor is configured with:

.. code-block:: xml

   <actor>
       <code_name>grayscale</code_name>
       <module>grayscale_actor</module>
       <enabled>true</enabled>
       
       <parameters>
           <parameter name="input_ids">equilibrium</parameter>
           <parameter name="output_ids">waves</parameter>
           <parameter name="power">1.0e6</parameter>
           <parameter name="frequency">170.0e9</parameter>
       </parameters>
       
       <inputs>
           <input>equilibrium</input>
           <input>core_profiles</input>
       </inputs>
       
       <outputs>
           <output>waves</output>
       </outputs>
   </actor>

**Actor Elements:**

* ``code_name`` - Actor identifier
* ``module`` - Python module name
* ``enabled`` - Whether to execute (true/false)
* ``parameters`` - Actor-specific parameters
* ``inputs`` - Required input IDS names
* ``outputs`` - Generated output IDS names

Time Evolution
~~~~~~~~~~~~~~

Configure time loop execution:

.. code-block:: xml

   <time_evolution>
       <start_time>0.0</start_time>
       <end_time>100.0</end_time>
       <time_step>1.0</time_step>
       <time_points>0.0,10.0,20.0,50.0,100.0</time_points>
   </time_evolution>

**Time Parameters:**

* ``start_time`` - Start time (seconds)
* ``end_time`` - End time (seconds)
* ``time_step`` - Time step increment
* ``time_points`` - Explicit time points (comma-separated)

Equilibrium Preparation
~~~~~~~~~~~~~~~~~~~~~~~

``HCDWorkflow.run()`` (``hcdworkflow/hcd_workflow.py``) prepares the input
equilibrium for the actors with ``hcdworkflow/equilibrium_extension.py``: psi
and B outside the LCFS and the ``profiles_2d`` grid are extended with
``workflow/extend_equilibrium.py`` (matched scheme), so that ray- and
beam-tracing actors see a smooth psi and B field from the launchers to the
plasma. Every entry point goes through ``HCDWorkflow.run()``: the stand-alone
Legacy driver (``hcd_nogui``, ``hcd_gui``), the Hybrid MUSCLE3 micro model and
JINTRAC, which calls ``HCDWorkflow.run()`` directly with the JETTO equilibrium,
so the same rule applies everywhere.

Optional entries of ``workflow_parameters``:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Parameter
     - Values
   * - ``eq_extension``
     - ``auto`` (default when neither ``eq_extension`` nor ``extend_equilibrium``
       is given), ``forced`` or ``disabled``. ``1`` and ``matched`` select
       ``auto``; ``0`` and ``none`` select ``disabled``. Values are
       case-insensitive; any other value stops the workflow with an error
       listing the accepted ones.
   * - ``extend_equilibrium``
     - Read when ``eq_extension`` is absent, with the same values.
   * - ``extend_equilibrium_box``
     - ``Rmin,Rmax,Zmin,Zmax`` in m, covered by the extended grid; when absent,
       the default box of ``extend_equilibrium.py`` (ITER EC launchers,
       ``3.9,10.6,-4.6,4.9``).

``auto`` decides per time slice from the equilibrium data
(``needs_extension()`` in ``extend_equilibrium.py``). The grid nodes of the
original ``profiles_2d`` grid with ``dx > 1.02`` are clearly outside the LCFS,
where ``dx`` is the normalised distance of the matched scheme (distance from the
magnetic axis divided by the distance of the LCFS at the same poloidal angle).
The slice is extended when

* more than 50 % of these nodes have psi clamped to the boundary value,
  ``|psi_N - 1| < 1e-4`` with ``psi_N = (psi - psi_axis) / (psi_boundary - psi_axis)``; or
* there is no such node (the grid stops at the plasma).

Otherwise, for instance for a free-boundary equilibrium whose psi varies outside
the LCFS, the slice is left unchanged; a slice without ``profiles_2d`` is also
left unchanged. ``forced`` extends every slice, e.g. to replace the extension
made by the equilibrium code itself; ``disabled`` never extends.

``HCDWorkflow.initialize()`` prints the setting used and where it comes from,
e.g. ``[equilibrium] extension setting: auto (extend_equilibrium = 1)``.
``HCDWorkflow.run()`` prints exactly one line per time slice, in every mode, e.g.
``[equilibrium] t=60.4064s extension: applied (auto: clamped fraction 1.000 of
808 nodes with dx>1.02): ...`` (JETTO), ``[equilibrium] t=199.9376s extension: not
applied (auto: clamped fraction 0.000 of 5834 nodes with dx>1.02, not needed)``
(DINA) or ``... extension: not applied (disabled)``; within JINTRAC this stdout
line is the record of the decision. JINTRAC initialises the workflow from
``Ext_HCD_WF_config``, so the setting is read from
``Ext_HCD_WF_config/input_workflow.xml``.

The actors receive an extended copy of the equilibrium; the equilibrium object
passed to ``HCDWorkflow.run()`` is not modified, and the stand-alone driver
writes the input equilibrium unchanged to the output entry. The extended copy is
not a reconstructed equilibrium outside the LCFS; the caveat is appended to its
``ids_properties.comment``.

``HCDWorkflow.run()`` also accepts the keywords ``eq_extension`` and
``eq_extension_box``, which take precedence over the workflow parameters.

Global Lists (YAML)
--------------------

Optional global parameters in ``global_lists.yaml``.

File Structure
~~~~~~~~~~~~~~

.. code-block:: yaml

   actors:
     - grayscale
     - nemo
     - torbeam
   
   databases:
     default: iterdb
     test: test_db
   
   paths:
     data_dir: /path/to/data
     output_dir: /path/to/output

Common Sections
~~~~~~~~~~~~~~~

**Actors List:**

.. code-block:: yaml

   actors:
     - grayscale
     - gray
     - torbeam
     - nemo

**Database Configuration:**

.. code-block:: yaml

   databases:
     production: iterdb
     development: devdb
     testing: testdb

**Path Configuration:**

.. code-block:: yaml

   paths:
     input_data: /work/imas/data/input
     output_data: /work/imas/data/output
     logs: /work/imas/logs

Waveform Files (YAML)
----------------------

Waveform data for time-varying parameters.

Structure
~~~~~~~~~

.. code-block:: yaml

   waveform_name:
     times: [0.0, 10.0, 20.0, 30.0]
     values: [1.0e6, 1.5e6, 2.0e6, 1.8e6]
     interpolation: linear

**Fields:**

* ``times`` - Time points (seconds)
* ``values`` - Parameter values at each time
* ``interpolation`` - Interpolation method (linear, cubic, step)

Example Waveform
~~~~~~~~~~~~~~~~

.. code-block:: yaml

   ec_power:
     times: [0.0, 5.0, 10.0, 15.0, 20.0]
     values: [0.0, 0.5e6, 1.0e6, 1.0e6, 0.5e6]
     interpolation: linear
     units: W
     description: "EC heating power ramp-up"
   
   ic_frequency:
     times: [0.0, 100.0]
     values: [50.0e6, 50.0e6]
     interpolation: step
     units: Hz
     description: "IC frequency (constant)"

Actor-Specific Configuration
-----------------------------

GRAYSCALE
~~~~~~~~~

.. code-block:: xml

   <parameters>
       <parameter name="power">1.0e6</parameter>
       <parameter name="frequency">170.0e9</parameter>
       <parameter name="launch_angle_tor">20.0</parameter>
       <parameter name="launch_angle_pol">0.0</parameter>
   </parameters>

NEMO
~~~~

.. code-block:: xml

   <parameters>
       <parameter name="beam_energy">1.0e6</parameter>
       <parameter name="beam_power">33.0e6</parameter>
       <parameter name="species">D</parameter>
   </parameters>

TORBEAM
~~~~~~~

.. code-block:: xml

   <parameters>
       <parameter name="frequency">170.0e9</parameter>
       <parameter name="power">1.5e6</parameter>
       <parameter name="mode">X</parameter>
   </parameters>

Validation
----------

Configuration Checks
~~~~~~~~~~~~~~~~~~~~

The workflow performs automatic validation:

* XML schema compliance
* Required parameters present
* Valid parameter types and ranges
* Actor dependencies satisfied
* IDS availability

Error Messages
~~~~~~~~~~~~~~

Common configuration errors:

* ``Missing required parameter: <name>``
* ``Invalid parameter value: <value>``
* ``Actor not found: <actor_name>``
* ``Circular dependency detected``
* ``Input IDS not available: <ids_name>``

Best Practices
--------------

1. **Use Comments:** Document your configuration

   .. code-block:: xml
   
      <!-- EC heating configuration for ramp-up phase -->

2. **Validate Before Running:** Check configuration syntax

3. **Version Control:** Keep configurations in git

4. **Modular Design:** Use separate files for different scenarios

5. **Descriptive Names:** Use clear parameter names

Examples
--------

See :doc:`../user/examples` for complete configuration examples.

See Also
--------

* :doc:`commands` - Command-line reference
* :doc:`actors` - Available actors
* :doc:`../user/usage` - Usage guide
