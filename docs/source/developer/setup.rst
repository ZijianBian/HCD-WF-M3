Developer setup
===============

Start with a source checkout and the runtime described in
:doc:`../user/installation`. On ITER SDCC, run these commands from the
repository root:

.. code-block:: bash

   source config_hcd_iter_sdcc.sh
   python -m pip install -e ".[dev]"

The helper selects the DD 4.1.0 / Intel-2023b / MUSCLE3 0.8.0 stack and
activates ``devenv_dd410``. The editable installation makes source changes
available without reinstalling the package. Actor binaries and IMAS input
data are separate requirements; see :doc:`actor_installation`.

Check the environment
---------------------

Before investigating a workflow failure, confirm which Python and IMAS
installation the shell is using:

.. code-block:: bash

   which python
   python -c "import imas; print(imas.__file__)"
   python -c "import libmuscle; print(libmuscle.__file__)"
   module list

Use ``config_hcd_iter_sdcc_3.42.0.sh`` in a separate shell only when working
on a Legacy DD 3.42.0 case. Do not combine its actors with the DD4 topology
templates.

Build the handbook
------------------

The ``dev`` extra includes the documentation dependencies. From the
repository root, build a local preview with:

.. code-block:: bash

   python -m sphinx -b html docs/source /tmp/hcdwf-handbook-preview

Open ``/tmp/hcdwf-handbook-preview/index.html`` in a browser. Edit the
``.rst`` sources under ``docs/source/`` and rebuild to see the result.
Generated HTML stays outside the checkout.

Choose a starting point
-----------------------

Read :doc:`architecture` for the execution paths, then use :doc:`api` to
find the module that owns the behavior you want to change. A physics run
needs the selected actors, valid input IDSs and a separate output run;
compilation or import checks alone do not verify its results. Contribution
and review guidance is in :doc:`contributing`.
