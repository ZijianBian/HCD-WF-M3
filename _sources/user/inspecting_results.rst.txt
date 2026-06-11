Inspecting Results
==================

Outputs are IMAS runs. The output location is defined by
``input_workflow.xml``.

Key Fields
----------

.. list-table::
   :header-rows: 1

   * - Field
     - Meaning
   * - ``output_user_or_path``
     - User/path for the output IMAS database.
   * - ``output_database``
     - Database name, often ``ITER``.
   * - ``output_backend``
     - Backend, for example ``HDF5`` or ``MDSPLUS``.
   * - ``shot_nr``
     - Shot number.
   * - ``run_out``
     - Output run number.

Inspect with IMAS Tools
-----------------------

Use the database, backend, shot, and run from the case configuration. On SDCC,
IDStools and IMAS-Python are the preferred stable ways to inspect IDS content.

For examples in documentation, use placeholder values such as:

.. code-block:: text

   database: ITER
   shot:     130012
   run:      6

MUSCLE Run Directories
----------------------

MUSCLE creates directories named like ``run_*``. Useful files include:

* ``configuration.ymmsl``: the exact topology that was launched.
* ``muscle3_manager.log``: manager-level events.
* ``instances/*``: stdout and stderr for each component.
* ``performance.sqlite``: timing database when enabled.

When debugging, start with the first component that exits nonzero, then inspect
the upstream actor that sent its last IDS.
