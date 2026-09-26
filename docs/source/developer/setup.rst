Developer setup
===============

Use Python 3.11 or newer and IMAS-Python, with the runtime described in
:doc:`../user/installation`. On ITER SDCC, run these commands from the
source checkout's root directory:

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

Legacy DD3 cases need an IMAS-Python environment and actors built for the
chosen DD3 release. Keep that stack separate from the DD4 topology runtime;
see :doc:`../user/installation`.

Code checks
-----------

GitHub Actions runs the Ruff checks for pull requests targeting ``develop``.
Run them locally from the repository root:

.. code-block:: bash

   ruff check
   ruff format --check

The actor regression scripts are under ``ci-sdcc/``. Set ``MODULES`` and
``TESTS`` as described in ``ci-sdcc/st03-regression.sh`` before running them.

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
