Available Actor Modules
========================

This page lists all actor modules available via EasyBuild at ``/work/imas/etc/modules/all``.

All modules are built with: **intel-2023b-DD-3.42.0**

Loading Modules
---------------

To load a module:

.. code-block:: bash

   module load <MODULE_NAME>/<VERSION>-intel-2023b-DD-3.42.0

Example:

.. code-block:: bash

   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0

Mandatory Actors
----------------

These actors are required for most HCD workflows:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Actor
     - Version
     - Description
   * - HCD_MERGERS
     - 1.0.0
     - Merges heating and current drive sources
   * - HCD2CORE_SOURCES
     - 1.2.0
     - Converts HCD outputs to core_sources IDS
   * - HCD2CORE_PROFILES
     - 1.1.0
     - Converts HCD outputs to core_profiles IDS

Electron Cyclotron (EC) Heating Actors
---------------------------------------

Ray tracing and EC heating/current drive codes:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Actor
     - Version
     - Description
   * - GRAYSCALE
     - 1.1.0
     - Advanced EC ray tracing (most commonly used)
   * - GRAY
     - 1.0.0
     - EC ray tracing and absorption
   * - TORBEAM
     - 3.8.0
     - EC beam tracing with wave effects
   * - TORAY
     - 1.0.0
     - EC ray tracing code
   * - GENRAY
     - 10.11.3
     - General ray tracing (EC and LH)

Ion Cyclotron (IC) Heating Actors
----------------------------------

IC heating and wave propagation codes:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Actor
     - Version
     - Description
   * - CYRANO
     - 1.0.0
     - IC heating code
   * - FoPla
     - 2.1.0
     - Fokker-Planck solver for IC
   * - StixReDist
     - 2.1.0
     - Stix wave redistribution
   * - TOMCAT
     - 1.0.0
     - IC wave code

Neutral Beam Injection (NBI) Actors
------------------------------------

Neutral beam injection and fast ion codes:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Actor
     - Version
     - Description
   * - NEMO
     - 2.2.0
     - NBI modeling code (most commonly used)
   * - NBISIM
     - 1.3.0
     - NBI simulation code
   * - RISK
     - 2.2.0
     - Fast ion slowing down
   * - SPOT
     - 2.4.0
     - NBI orbit following

Other Actors
------------

Additional simulation and analysis actors:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Actor
     - Version
     - Description
   * - RELAX
     - 1.0.0
     - Fokker-Planck code
   * - SMART
     - 0.1.0
     - Analysis tool
   * - FPSIM
     - 1.0.0
     - Fokker-Planck simulation

Complete Module List
--------------------

For reference, here's the complete list of available modules:

.. code-block:: bash

   # Mandatory
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0
   
   # EC Heating
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load GRAY/1.0.0-intel-2023b-DD-3.42.0
   module load TORBEAM/3.8.0-intel-2023b-DD-3.42.0
   module load TORAY/1.0.0-intel-2023b-DD-3.42.0
   module load GENRAY/10.11.3-intel-2023b-DD-3.42.0
   
   # IC Heating
   module load CYRANO/1.0.0-intel-2023b-DD-3.42.0
   module load FoPla/2.1.0-intel-2023b-DD-3.42.0
   module load StixReDist/2.1.0-intel-2023b-DD-3.42.0
   module load TOMCAT/1.0.0-intel-2023b-DD-3.42.0
   
   # NBI
   module load NEMO/2.2.0-intel-2023b-DD-3.42.0
   module load NBISIM/1.3.0-intel-2023b-DD-3.42.0
   module load RISK/2.2.0-intel-2023b-DD-3.42.0
   module load SPOT/2.4.0-intel-2023b-DD-3.42.0
   
   # Other
   module load RELAX/1.0.0-intel-2023b-DD-3.42.0
   module load SMART/0.1.0-intel-2023b-DD-3.42.0
   module load FPSIM/1.0.0-intel-2023b-DD-3.42.0

Checking Available Modules
---------------------------

To see all available modules on your system:

.. code-block:: bash

   module av HCD
   module av GRAYSCALE
   module av NEMO

To see currently loaded modules:

.. code-block:: bash

   module list

Module Dependencies
-------------------

Most actor modules automatically load their dependencies, including:

* IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
* Required numerical libraries (Intel MKL, HDF5, etc.)
* Python packages

You typically don't need to manually load these dependencies.

Usage Example
-------------

Typical module loading sequence for an EC heating simulation:

.. code-block:: bash

   # Load workflow
   module load HCD-WF
   
   # Load mandatory actors
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0
   
   # Load EC actor
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   
   # Run simulation
   hcd_nogui -c my_simulation/

See Also
--------

* :doc:`../user/installation` - Installation guide
* :doc:`../user/quickstart` - Quick start guide
* :doc:`actors` - Complete actor reference with GIT repositories
