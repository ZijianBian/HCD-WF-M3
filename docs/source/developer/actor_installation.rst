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
   merge_waves/merge_waves_m3.exe
   hcd2core_sources/hcd2core_sources_m3.exe
   rabbit/rabbit_m3.exe

The maintained yMMSL files use ``tools/hcdwf_m3_component`` to resolve these
executables below ``ACTOR_FOLDER``.

Rabbit GCC Runtime
------------------

Rabbit is built with GCC while the other validated HCD actors use Intel. Do not
load both runtime stacks into one process. Source the normal HCD environment:

.. code-block:: bash

   source config_hcd_iter_sdcc.sh

Then launch Rabbit through ``tools/run_rabbit_m3_gcc_2023b.sh`` or
``hcdwf_pure_rabbit_m3.ymmsl``. The launcher purges modules only in the Rabbit
child process and loads the GCC/foss IMAS-Fortran, MUSCLE3, XMLlib, and INTERPOS
modules. Both sides retain the DD 4.1.0 and MUSCLE3 0.8 data contract.

The Rabbit source tree, build products, and build logs belong under the external
actor installation, not in the HCDWF repository.

Validation Rule
---------------

After building or changing an actor:

1. Run a single-slice case.
2. Run a short multi-slice case.
3. Compare against Legacy or Hybrid with identical physics settings.
