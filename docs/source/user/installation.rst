Installation
============

HCD-WF needs an IMAS environment and compiled physics actors. Installing the
Python package alone does not provide those actors or the input databases.

From a source checkout on SDCC
------------------------------

Use the checkout whose code matches this handbook. In its root directory:

.. code-block:: bash

   export ACTOR_FOLDER=/path/to/PYTHON_ACTORS
   source config_hcd_iter_sdcc.sh
   python -m pip install -e .

The helper loads the pinned DD 4.1.0 / Intel-2023b / MUSCLE3 0.8.0 stack and
activates ``devenv_dd410``. The editable install is a one-time step; source
the helper again when opening a new shell.

Set ``ACTOR_FOLDER`` to the directory containing actor packages such as
``torbeam/`` and ``cyrano/``. Without this setting, the helper uses
``PYTHON_ACTORS/`` below the checkout. Legacy and Hybrid need the iWrap
packages; Pure needs the native MUSCLE3 executables required by its topology. See
:doc:`../developer/actor_installation` if they are not already installed.

Sourcing the helper does not install packages by default. The available path
overrides are listed in :doc:`../reference/available_modules`.

Existing module installations
-----------------------------

If your site provides an HCD-WF module, load it and inspect its console entry:

.. code-block:: bash

   module load HCD-WF
   hcd_nogui --help

Use the documentation shipped with that release. The source-checkout
``run.sh`` and topology templates described here are not supplied by every
installed module.

Older DD 3.42.0 cases
---------------------

For Legacy actors built against DD 3.42.0, use a separate shell:

.. code-block:: bash

   source config_hcd_iter_sdcc_3.42.0.sh
   python -m pip install -e .

This helper uses ``devenv_3.42.0``. If ``ACTOR_FOLDER`` is set, it uses
that actor installation; otherwise it loads the listed Legacy actor modules.
Keep the case, actor builds and IMAS stack compatible. The DD 3.42.0 helper
does not prepare the MUSCLE3 topologies in this handbook.

Once the environment is ready, continue with :doc:`quickstart`.
