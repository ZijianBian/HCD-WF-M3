Installation
============

Recommended SDCC Setup
----------------------

For current development work, start each shell session from the repository root:

.. code-block:: bash

   source config_hcd_iter_sdcc.sh

This is the preferred setup for the M3 branch. It configures:

* IMAS-Python and the DD 4.1.0 stack.
* MUSCLE3.
* iWrap and actor paths.
* Waveform Cooker.
* The local ``devenv`` Python environment.

Legacy DD 3.42.0 Setup
----------------------

Use the older helper only for compatibility tests:

.. code-block:: bash

   source config_hcd_iter_sdcc_3.42.0.sh

This creates and uses a separate ``devenv_3.42.0`` environment so it does not
mix with the DD 4.1.0 development stack.

Editable Python Install
-----------------------

The helper script normally installs the package for you. If you need to do it
manually:

.. code-block:: bash

   python -m venv devenv --system-site-packages
   source devenv/bin/activate
   python -m pip install -e .

Documentation Dependencies
--------------------------

To build this manual locally:

.. code-block:: bash

   ./devenv/bin/python -m pip install -e ".[docs]"
   cd docs
   ../devenv/bin/python -m sphinx -M html source build

Open the generated page:

.. code-block:: text

   docs/build/html/index.html

Actor Availability
------------------

Most users should rely on the SDCC module stack or the actor folder configured
by ``config_hcd_iter_sdcc.sh``. Developers who need custom actors can set:

.. code-block:: bash

   ACTOR_FOLDER=/path/to/PYTHON_ACTORS source config_hcd_iter_sdcc.sh

Pure M3 mode requires M3-capable actor executables such as
``torbeam_m3.exe`` and ``cyrano_m3.exe``.
