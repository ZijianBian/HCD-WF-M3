Actor Installation
==================

Most users should not build actors manually. Use the SDCC module stack or the
actor folder configured by ``config_hcd_iter_sdcc.sh``.

When You Need This
------------------

Manual actor installation is useful when:

* Testing a modified actor.
* Building an M3-capable direct actor executable.
* Reproducing a specific actor revision.

Actor Folder
------------

Set ``ACTOR_FOLDER`` before sourcing the environment helper:

.. code-block:: bash

   ACTOR_FOLDER=/path/to/PYTHON_ACTORS source config_hcd_iter_sdcc.sh

The workflow and yMMSL files should then point to actor wrappers or executable
files inside that folder.

Classic iWrap Actors
--------------------

Classic Legacy and Hybrid mode use iWrap actors loaded into Python.

The old ``actor_install.py`` workflow can still be used for actor development,
but it is not the first path for normal users.

Pure M3 Actors
--------------

Pure M3 mode needs actor executables such as:

.. code-block:: text

   torbeam/torbeam_m3.exe
   cyrano/cyrano_m3.exe
   rabbit/rabbit_m3.exe
   merge_waves/merge_waves_m3.exe
   hcd2core_sources/hcd2core_sources_m3.exe

The yMMSL file must point to the executable paths explicitly.

Rabbit Reference Build
----------------------

The HCD DD 4.1.0/MUSCLE3 0.8 stack cannot exchange messages with the original
DD 4.1.1/MUSCLE3 0.10 collaborator build, even though both are GCC builds. The
accepted Rabbit executable was rebuilt from Rabbit ``master`` commit
``e99ad70`` with GCC 13.2, IMAS-Fortran 5.5.0-foss-2023b-DD-4.1.0, and
MUSCLE3 0.8.0-foss-2023b.

Apply the workflow compatibility fixes from the Rabbit source root before
building:

.. code-block:: bash

   git apply /path/to/hcd-wf/actor_install/rabbit_master_e99ad70_hcdwf_minimal.patch

The minimal patch contains the DD4 radial-grid fallback, non-contiguous species
compression fix, collision-ion metadata, and the scalar equivalent of the Redl
expression needed to avoid a GCC 13 front-end failure. Keep both builds
versioned when installing:

.. code-block:: text

   rabbit_m3_gcc2023b_dd410_muscle08.exe   # HCD Pure M3
   rabbit_m3_gcc2025b_dd411_muscle010.exe  # collaborator stack

``tools/run_rabbit_m3_gcc_2023b.sh`` loads the compatible runtime in Rabbit's
own process, so the remaining Intel-built HCD actors do not inherit GCC
libraries.

Validation Rule
---------------

After building or changing an actor:

1. Run a single-slice case.
2. Run a short multi-slice case.
3. Compare against Legacy or Hybrid with identical physics settings.
