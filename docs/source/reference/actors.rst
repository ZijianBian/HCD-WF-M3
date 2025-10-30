Available Actors
================

This page lists all available H&CD actors that can be used with the workflow.

Actor Categories
----------------

The HCD Workflow supports actors in the following categories:

* **Workflow Components** - Core workflow and merger actors
* **Electron Cyclotron (EC)** - ECRH wave solvers
* **Ion Cyclotron (IC)** - ICRH coupling, wave, and Fokker-Planck solvers
* **Neutral Beam Injection (NBI)** - NBI source and Fokker-Planck solvers
* **Nuclear Reactions** - Nuclear source and related solvers
* **IDS Fillers** - Transport solver integration actors

Complete Actor List
-------------------

Workflow Components
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - **Actor Name**
     - **Project Name**
     - **Git Repository**
   * - (workflow)
     - hcd-wf
     - ssh://git@git.iter.org/wf/hcd-wf.git
   * - merge_distribution_sources
     - hcd-mergers
     - ssh://git@git.iter.org/heat/hcd-mergers.git
   * - merge_distributions
     - hcd-mergers
     - ssh://git@git.iter.org/heat/hcd-mergers.git
   * - merge_waves
     - hcd-mergers
     - ssh://git@git.iter.org/heat/hcd-mergers.git
   * - waveform-cooker
     - waveform-cooker
     - ssh://git@git.iter.org/imex/waveform-cooker.git

Electron Cyclotron (ECRH)
~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| torbeam                    | TORBEAM                    | ssh://git@git.iter.org/heat/torbeam.git     |
+----------------------------+----------------------------+---------------------------------------------+
| gray                       | GRAY                       | ssh://git@git.iter.org/heat/gray.git        |
+----------------------------+----------------------------+---------------------------------------------+
| grayscale                  | GRAYSCALE                  | ssh://git@git.iter.org/heat/grayscale.git   |
+----------------------------+----------------------------+---------------------------------------------+
| genray                     | GENRAY                     | ssh://git@git.iter.org/heat/genray.git      |
+----------------------------+----------------------------+---------------------------------------------+
| toray                      | TORAY                      | ssh://git@git.iter.org/heat/toray.git       |
+----------------------------+----------------------------+---------------------------------------------+

**Note**: Currently no EC Fokker-Planck calculation is available in IMAS, but will be added once implemented.

Ion Cyclotron (ICRH)
~~~~~~~~~~~~~~~~~~~~

**IC Coupling:**

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| iccoup                     | FPSIM                      | ssh://git@git.iter.org/heat/fpsim.git       |
+----------------------------+----------------------------+---------------------------------------------+

**IC Wave Solvers:**

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| cyrano                     | CYRANO                     | ssh://git@git.iter.org/heat/cyrano.git      |
+----------------------------+----------------------------+---------------------------------------------+
| pion                       | PION                       | ssh://git@git.iter.org/heat/pion.git        |
+----------------------------+----------------------------+---------------------------------------------+
| lion                       | LION                       | ssh://git@git.iter.org/heat/lion.git        |
+----------------------------+----------------------------+---------------------------------------------+
| tomcat                     | TOMCAT                     | ssh://git@git.iter.org/heat/tomcat.git      |
+----------------------------+----------------------------+---------------------------------------------+

**IC Fokker-Planck Solvers:**

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| stixredist                 | STIXREDIST                 | ssh://git@git.iter.org/heat/stixredist.git  |
+----------------------------+----------------------------+---------------------------------------------+
| fopla                      | FOPLA                      | ssh://git@git.iter.org/heat/fopla.git       |
+----------------------------+----------------------------+---------------------------------------------+

Neutral Beam Injection (NBI) and Nuclear Reactions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**NBI Particle Sources:**

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| nemo                       | NEMO                       | ssh://git@git.iter.org/heat/nemo.git        |
+----------------------------+----------------------------+---------------------------------------------+
| bbnbi_parallel             | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+
| bbnbi_serial               | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+

**NBI Fokker-Planck Solvers:**

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| risk                       | RISK                       | ssh://git@git.iter.org/heat/risk.git        |
+----------------------------+----------------------------+---------------------------------------------+
| spot                       | SPOT                       | ssh://git@git.iter.org/heat/spot.git        |
+----------------------------+----------------------------+---------------------------------------------+
| nbisim                     | NBISIM                     | ssh://git@git.iter.org/heat/nbisim.git      |
+----------------------------+----------------------------+---------------------------------------------+
| ascot_parallel             | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+
| ascot_serial               | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+
| ascot4rfof_parallel        | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+
| ascot4rfof_serial          | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+

**Nuclear Reactions:**

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| afsi                       | ASCOT                      | ssh://git@git.iter.org/traj/ascot.git       |
+----------------------------+----------------------------+---------------------------------------------+

**Note**: ASCOT actors can handle:

* NBI particle source
* Nuclear reactions particle source
* NBI and nuclear reactions Fokker-Planck solver
* IC-accelerated ions Fokker-Planck solver

Lower Hybrid Current Drive (LHCD)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------------------+----------------------------+---------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                          |
+============================+============================+=============================================+
| lhcd_metis                 | LHCD-METIS                 | Contact maintainers for access              |
+----------------------------+----------------------------+---------------------------------------------+

IDS Fillers for Transport Solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------------------+----------------------------+--------------------------------------------------+
| **Actor Name**             | **Project Name**           | **Git Repository**                               |
+============================+============================+==================================================+
| hcd2core_sources           | HCD2CORE-SOURCES           | ssh://git@git.iter.org/heat/hcd2core-sources.git |
+----------------------------+----------------------------+--------------------------------------------------+
| hcd2core_profiles          | HCD2CORE-PROFILES          | ssh://git@git.iter.org/heat/hcd2core-profiles.git|
+----------------------------+----------------------------+--------------------------------------------------+

Requesting Access
-----------------

To request access to actor repositories:

1. Go to the `IMAS S/W Repository Access form <https://jira.iter.org/servicedesk/customer/portal/1/create/257>`_
2. Request access to repositories you need:
   
   **Minimum Recommended Set:**
   
   * HCD WF (the workflow itself)
   * HCD Mergers (mandatory)
   * Waveform Cooker (highly recommended)
   * At least one heating source actor (EC, IC, or NBI)

3. Wait for approval
4. Clone and compile as described in :doc:`../developer/setup`

Actor Installation Methods
---------------------------

Method 1: Compile Actors (Developers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have GIT repository access:

.. code-block:: bash

   cd actor_install
   
   # Compile all actors you have access to
   python actor_install.py *.yml --SkipModules
   
   # Or compile specific actors
   python actor_install.py grayscale.yml --SkipModules
   python actor_install.py nemo.yml --SkipModules

Method 2: Load Pre-compiled HCD Actors using Easybuild modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For quick setup or if you don't have GIT access:

.. code-block:: bash

   # Copy from shared location (ITER SDCC)
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0

**Note**: The version ``DD-3.52.0`` refers to specific IMAS versions. If you work with another IMAS version, you need to comiple the actor for that IMAS version

Method 3: EasyBuild Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For users who just want to run simulations:

.. code-block:: bash

   module load HCD-WF

This automatically provides access to all necessary actors.

Actor Configuration
-------------------

Each actor has its own configuration file located in:

.. code-block:: text

   <config_folder>/<CATEGORY>/<process>/<actor_name>/

For example:

.. code-block:: text

   my_config/ECRH/ec_wave_solver/grayscale/input_grayscale.xml

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

Actor parameters are defined in XSD schema files that specify:

* Parameter names and descriptions
* Valid value ranges
* Data types
* Default values

The GUI provides:

* Hover tooltips with parameter descriptions
* Red background warning for out-of-range values
* Validation before execution

Actor Dependencies
------------------

Some actors require other actors to be run first. These dependencies are defined in ``global_lists.yaml``:

Example Prerequisites
~~~~~~~~~~~~~~~~~~~~~

* **ec_wave_fp** (RELAX) requires **ec_wave_solver** (any)
* **ic_wave_fp** (FOPLA) requires:
  
  * **ic_wave_solver** (any)
  * **nbi_source** (any)
  * **nbi_fp** (any)

* **nbi_fp** (RISK, SPOT, ASCOT, NBISIM) requires **nbi_source** (NEMO or BBNBI)
* **nuclear_fp** requires **nuclear_source** (AFSI via BBNBI)

Actor Capabilities
------------------

By Actor Type
~~~~~~~~~~~~~

**Wave Solvers**: Calculate wave propagation and absorption

* Input: equilibrium, core_profiles, launcher/antenna geometry
* Output: waves IDS with power deposition profiles

**Fokker-Planck Solvers**: Calculate particle distribution evolution

* Input: waves, core_profiles, source data
* Output: distributions IDS

**Source Codes**: Calculate particle source terms

* Input: geometry, equilibrium, core_profiles
* Output: distribution_sources IDS

**Mergers**: Combine results from multiple actors

* Input: Multiple IDSs of same type from different actors
* Output: Single merged IDS

**IDS Fillers**: Convert to transport-solver format

* Input: H&CD results (waves, distributions, etc.)
* Output: core_sources or core_profiles IDS

Troubleshooting
---------------

Actor Not Found
~~~~~~~~~~~~~~~

If an actor is not available:

1. Check if you requested repository access
2. Verify the actor was compiled successfully
3. Check ``ACTOR_FOLDER`` environment variable
4. For EasyBuild users, verify the HCD-WF module version

Compilation Errors
~~~~~~~~~~~~~~~~~~

If actor compilation fails:

1. Check IMAS version compatibility
2. Verify all dependencies are loaded
3. Check for missing GIT repository access
4. Review build logs in ``actor_install/build-<DATE>-<TIME>/``

Actor Execution Errors
~~~~~~~~~~~~~~~~~~~~~~

If an actor fails during execution:

1. Check input IDS validity
2. Verify parameter ranges in configuration
3. Review actor-specific log files (if configured)
4. Check dependencies are satisfied
5. Verify IMAS version compatibility

Contact Information
-------------------

For actor-specific issues:

* **HCD Workflow & Mergers**: Mireille Schneider
* **Waveform Cooker**: Check IMAS documentation
* **Specific Actors**: Refer to individual actor documentation

See Also
--------

* :doc:`../user/installation` - Installation instructions
* :doc:`../user/usage` - How to configure and use actors
* :doc:`../developer/setup` - Actor compilation and development
* :doc:`configuration` - Configuration file formats
