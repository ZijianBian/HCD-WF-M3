Contributing
============

Keep changes small, measurable, and tied to a run or test.

Before Editing
--------------

Check the working tree:

.. code-block:: bash

   git status --short

Do not mix unrelated generated run directories with source changes.

Code Checks
-----------

For Python-only changes:

.. code-block:: bash

   python3 -m py_compile workflow/wf_wrapper.py workflow/ids_prep.py hcdworkflow/workflow_driver_m3_direct.py
   pytest tests/test_ids_prep.py

For workflow behavior, record:

* Mode.
* Shot/run.
* Time range.
* ``dt_required``.
* Actor selection.
* ``ic_toroidal_modes.yaml`` state.
* Output run number.

Documentation Checks
--------------------

Build the docs before publishing documentation changes:

.. code-block:: bash

   cd docs
   ../devenv/bin/python -m sphinx -M html source build

Documentation Style
-------------------

Prefer short operational pages over long generated prose. Every main user page
should answer one practical question and link to deeper reference material.

Benchmark Notes
---------------

A benchmark is valid only if the physics work is identical across modes. Record
whether weighted IC toroidal modes are enabled, whether FoPla is enabled, and
which time slices were run.
