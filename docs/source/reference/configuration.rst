Configuration Reference
=======================

The main case configuration is ``input_workflow.xml`` in the configuration
folder. Optional YAML files provide waveforms and IC toroidal mode settings.

``input_workflow.xml``
----------------------

The real root element is ``<root>``. The important sections are
``workflow_parameters`` and ``actor_selection``.

Workflow Parameters
~~~~~~~~~~~~~~~~~~~

Example:

.. code-block:: xml

   <workflow_parameters display="Workflow parameters (standalone)">
     <input_user_or_path display="Input user or path">public</input_user_or_path>
     <input_database display="Input database">ITER</input_database>
     <input_backend display="Input backend">HDF5</input_backend>
     <shot_nr display="Input shot">130012</shot_nr>
     <run_in display="Input run">5</run_in>
     <output_user_or_path display="Output user or path">public</output_user_or_path>
     <output_database display="Output database">ITER</output_database>
     <output_backend display="Output backend">HDF5</output_backend>
     <run_out display="Output run">6</run_out>
     <tbegin display="Start Time [s]">10.</tbegin>
     <tend display="End Time   [s]">320.</tend>
     <dt_required display="Time Step  [s]">5</dt_required>
     <parallel_workflow display="Parallel workflow [0-1]">0</parallel_workflow>
     <one_time_slice display="Single time slice [0-1]">0</one_time_slice>
   </workflow_parameters>

Common fields:

.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``shot_nr``
     - Input and output shot number.
   * - ``run_in``
     - Input scenario run.
   * - ``run_out``
     - Output run to write.
   * - ``tbegin`` / ``tend``
     - Time interval for the workflow loop.
   * - ``dt_required``
     - Requested time step.
   * - ``one_time_slice``
     - ``1`` for a single-slice run, ``0`` for a loop.

Actor Selection
~~~~~~~~~~~~~~~

Actor values are integer selections from each ``list`` attribute. ``0`` means
disabled.

Example:

.. code-block:: xml

   <ECRH display="ECH">
     <ec_wave_solver display="Wave solver" list="genray gray grayscale torbeam toray">4</ec_wave_solver>
   </ECRH>

   <ICRH display="ICRH">
     <ic_wave_solver display="Wave solver" list="cyrano tomcat pion lion">1</ic_wave_solver>
     <ic_wave_fp display="Ion Fokker-Planck" list="stixredist fopla">0</ic_wave_fp>
   </ICRH>

   <source display="Fill core_sources">
     <fill_core_sources display="core_sources IDS" list="hcd2core_sources">1</fill_core_sources>
   </source>

For the corrected benchmark:

* ``ec_wave_solver=4`` selects Torbeam.
* ``ic_wave_solver=1`` selects Cyrano.
* ``ic_wave_fp=0`` disables FoPla.
* ``fill_core_sources=1`` enables hcd2core_sources.

``ic_toroidal_modes.yaml``
--------------------------

This file controls weighted multi-``Ntor`` Cyrano runs in the classic workflow
path.

For single-``Ntor`` comparison:

.. code-block:: yaml

   enabled: false
   modes: []

For a weighted spectrum:

.. code-block:: yaml

   enabled: true
   modes:
     - n_phi: -38
       weight: 0.5
     - n_phi: 38
       weight: 0.5

Do not compare weighted and unweighted cases as mode-level performance results.

yMMSL Files
-----------

Hybrid and Pure M3 runs need a yMMSL file.

Hybrid yMMSL wires:

.. code-block:: text

   workflow_driver <-> hcd_workflow

Pure yMMSL wires:

.. code-block:: text

   driver <-> torbeam
   driver <-> cyrano
   driver <-> merge_waves
   driver <-> hcd2core_sources

The ``settings.config_folder_path`` value must point to the configuration
folder containing ``input_workflow.xml`` and actor parameter files.
