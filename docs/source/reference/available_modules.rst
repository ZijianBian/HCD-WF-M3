Runtime modules
===============

The source checkout provides two SDCC setup scripts. Choose the one matching
your actor build; :doc:`../user/installation` describes the setup procedure.
The versions below record what those scripts load, rather than a live catalog
of everything available on SDCC.

Default: DD 4.1.0
-----------------

``config_hcd_iter_sdcc.sh`` loads these exact modules:

.. code-block:: text

   IMAS-Python/2.3.0-intel-2023b
   IMAS-Fortran/5.5.0-intel-2023b-DD-4.1.0
   MUSCLE3/0.8.0-intel-2023b
   XMLlib/3.2.0-intel-compilers-2023.2.1
   INTERPOS/9.2.0-iimkl-2023b
   Tkinter/3.11.5-GCCcore-13.2.0
   Waveform-Cooker/1.6.0-GCCcore-13.2.0

Actors are taken from ``ACTOR_FOLDER`` (default: ``PYTHON_ACTORS`` under the
source checkout). The script creates or activates ``devenv_dd410`` with access
to the module-provided Python packages; it does not install the actors.

Rabbit runs in a separate GCC process. ``topologies/pure.ymmsl`` calls
``scripts/run_rabbit_m3.sh``, which loads
``IMAS-Fortran/5.5.0-foss-2023b-DD-4.1.0``, ``XMLlib/3.3.2-GCC-13.2.0``,
``INTERPOS/9.2.0-gfbf-2023b`` and ``MUSCLE3/0.8.0-foss-2023b`` for that process.

Legacy: DD3.42
--------------

``config_hcd_iter_sdcc_3.42.0.sh`` uses the regression stack: IMAS-Python
2.3.0, iWrap 2.0.0 and IMAS-Fortran 5.6.0 with DD3.42.2, plus their pinned
dependencies. The historical filename is retained; this is an IMAS-Python
environment, with actors built for DD3.42.2 and a separate ``virtualenvdir``.
See :doc:`../user/installation`.

Checking the active environment
-------------------------------

.. code-block:: bash

   module list
   module avail IMAS
   module avail MUSCLE3
   module avail TORBEAM

Both SDCC helpers purge previously loaded modules. ``HCDWF_VENV_DIR`` overrides
their virtual-environment path. Dependency installation is skipped by default;
set ``HCDWF_SKIP_PIP_INSTALL=0`` before sourcing a helper to request an editable
installation of the checkout.

``config_hcd_iter_hpc.sh`` is an older, separate HPC setup based on the 2018
module stack. It does not select the DD 4.1.0 environment described above.
