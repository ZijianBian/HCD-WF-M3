Configuration reference
=======================

The :doc:`../user/gui` saves a configuration directory with this layout:

.. code-block:: text

   my_config/
   ├── input_workflow.xml
   ├── ECRH/ec_wave_solver/input_torbeam.xml
   ├── ICRH/ic_wave_solver/input_cyrano.xml
   ├── source/fill_core_sources/input_hcd2core_sources.xml
   └── *_waveforms.yaml                 # optional waveform overrides

Only selected actors need parameter files. The GUI also copies their XSD
schemas when available. Input and output IDS reside in IMAS database entries;
they do not need to be copied into this directory.

Workflow XML
------------

``input_workflow.xml`` has a ``root`` element whose first two children are
``workflow_parameters`` and ``actor_selection``, in that order. The former holds
the database and time fields directly; the latter groups actors under
``main_process`` and ``post_process``. The shipped template is
``hcdworkflow/global_configuration/input_workflow_default.xml``.

Database fields in ``workflow_parameters``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Field
     - Meaning
   * - ``input_user_or_path``, ``input_database``
     - User or path, and database containing the input scenario
   * - ``input_backend``
     - IMAS backend name, such as ``HDF5`` or ``MDSPLUS``
   * - ``shot_nr``, ``run_in``
     - Input shot and run
   * - ``output_user_or_path``
     - Output user or path; ``default`` resolves to the current user
   * - ``output_database``
     - Output database; ``default`` uses the input database name
   * - ``output_backend``
     - Output IMAS backend; set it explicitly in saved configurations
   * - ``run_out``
     - Output run, under the same ``shot_nr``
   * - ``ddv_backend``
     - Optional DD value passed to the database helper. If omitted, the driver
       uses ``IMAS_VERSION`` or the DD version reported by the IMAS installation

Choose a separate output entry when retaining earlier results: the driver
creates the configured output entry at startup. The DD 4.1.0 environment and
the legacy DD 3.42.0 environment are described in :doc:`available_modules`.

Time and scheduling
-------------------

``tbegin``, ``tend``, ``dt_required``
   Start, end and step in seconds. Use a positive step. The time loop visits
   ``tbegin + n * dt_required`` while the time is strictly less than ``tend``;
   the end time is excluded. In a multi-slice run, a negative start or end uses
   the first or last equilibrium time respectively.

``one_time_slice``
   ``1`` runs once at ``tbegin`` and ignores the configured ``tend``. ``0`` uses
   the time range above. This applies to Legacy, Hybrid and Pure drivers.

``parallel_workflow``
   Retained in the XML template, but not read by the current runtime. It does
   not select an execution mode or enable parallel execution. Pure scheduling
   uses yMMSL settings; see :doc:`../user/execution_modes`.

The GUI can append a third ``time_base`` section for per-process schedules.
Legacy and Hybrid read those schedules; Pure does not use this section.

Actor selection
---------------

Each process element has an integer value: ``0`` disables it; ``1`` selects the
first actor in that element's ``list`` attribute, ``2`` the second, and so on.
For example, this fragment selects Torbeam:

.. code-block:: xml

   <ECRH>
     <ec_wave_solver list="genray gray grayscale torbeam toray">4</ec_wave_solver>
     <ec_wave_fp list="relax">0</ec_wave_fp>
   </ECRH>

The XML ``list`` attribute determines the mapping. Preserve its order when
editing a saved configuration. :doc:`actors` lists the shipped choices.
The ``display`` attributes provide GUI labels.

Actor parameters belong in
``CATEGORY/PROCESS/input_ACTOR.xml``, for example
``NBI/nbi_fp/input_rabbit.xml``. Their fields come from each actor's own XML/XSD;
there is no shared ``<parameters><parameter name="...">`` format.

Waveforms and shared settings
-----------------------------

Files such as ``ec_waveforms.yaml``, ``ic_waveforms.yaml`` and
``nbi_waveforms.yaml`` sit beside ``input_workflow.xml``. The driver passes them
to Waveform-Cooker to replace the corresponding machine-description IDS.
Use its presets or the GUI waveform editor for their format. Without an
override, the driver uses machine descriptions from the input scenario.

Legacy and Hybrid also read an optional ``ic_toroidal_modes.yaml`` beside the
workflow XML for Cyrano. Its ``modes`` list contains ``n_phi`` integers and
positive ``weight`` values (default ``1.0``); the workflow normalizes the
weights and combines the per-mode wave outputs. Set ``enabled: false`` to
disable it. The Pure driver does not read this file.

``hcdworkflow/global_configuration/global_lists.yaml`` is a package resource,
not an optional per-run configuration. It contains registered actors, execution
orders, dependencies and waveform preset names.

For MUSCLE3, yMMSL describes components and connections. ``run.sh`` and the GUI
copy the chosen topology into ``.hcd_gui_runs/`` and bind it to the saved
configuration and actor parameter files. Pure also keeps only the components
and connections needed by ``actor_selection``.
See :doc:`../user/execution_modes` for the two supplied templates and
:doc:`commands` for output locations.
