Troubleshooting
===============

Zero IC Power
-------------

If the IC waveform is off, Pure mode should not run Cyrano or FoPla. Look for:

.. code-block:: text

   Skipping Cyrano because IC launched power is zero
   Skipping FoPla because IC launched power is zero
   Skipping merge_waves because IC launched power is zero

If an actor still runs on a zero-power IC slice, check the yMMSL wiring and the
active actor set printed by the driver.

FoPla After IC Turns Off
------------------------

Do not force FoPla to run after IC power is off. FoPla can renormalize to its
XML target power and produce misleading behavior even when the launched power
waveform is zero.

Wave Merge Fails
----------------

``merge_waves`` needs active wave branches. If only EC or only IC is active,
the Pure driver should bypass the merge and carry the active branch forward.

Unfair Runtime Comparison
-------------------------

Before comparing modes, check ``ic_toroidal_modes.yaml``. A weighted
``Ntor=-38/+38`` legacy or hybrid case does more Cyrano work than a
single-``Ntor`` Pure case.

MUSCLE Component Crash
----------------------

Start with the manager log:

.. code-block:: text

   run_*/muscle3_manager.log

Then inspect the component instance directories:

.. code-block:: text

   run_*/instances/<component>/

The first component with a nonzero exit is usually the useful one. The next
place to inspect is the actor immediately upstream in the yMMSL conduit graph.

Result Inspection
-----------------

Use the output location configured in ``input_workflow.xml``. For stable
inspection workflows, prefer IDStools or IMAS-Python scripts over experimental
GUI tools.

Sphinx Build Fails
------------------

Install the docs extras and rebuild:

.. code-block:: bash

   ./devenv/bin/python -m pip install -e ".[docs]"
   cd docs
   ../devenv/bin/python -m sphinx -M html source build
