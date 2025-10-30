Actor Installation Script
=========================

Overview
--------

The ``actor_install.py`` script automates the process of downloading, building, and installing IMAS actors from source repositories. It uses YAML configuration files to define the build process for each actor.

Usage
-----

.. code-block:: bash

   python actor_install.py [OPTIONS] <yaml_file1> [yaml_file2 ...]

Command Line Options
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``-M``, ``--preModule MODULE``
     - Load a specific module before setup (e.g., if imasenv is not available by default). This works even with ``--skipModules`` to load a base module before using pre-loaded modules.
   * - ``-D``, ``--workDir DIR``
     - Specify working directory for sources (default: ``build_YYYY-MM-DD_HHhMMmSSs``)
   * - ``-R``, ``--checkRevision``
     - Verify that checked-out sources match expected revision/hash. For git: compares commit hash if VERSION is a 40-character hash, otherwise verifies branch/tag name. For svn: compares revision number.
   * - ``--skipModules``
     - Skip environment module setup (use current environment). **Warning:** You must manually load all required modules listed in the YAML file's MODULES section before running the script.
   * - ``--skipSources``
     - Skip source code checkout (use existing sources)
   * - ``--skipBuilds``
     - Skip library building step
   * - ``--skipActors``
     - Skip actor installation step
   * - ``-v``, ``--verbose``
     - Run in verbose mode with detailed output
   * - ``-p``, ``--pedantic``
     - Stop entire script at first error

Examples
~~~~~~~~

.. code-block:: bash

   # Full installation
   python actor_install.py grayscale.yml

   # Skip module setup if already configured
   # WARNING: You must manually load all required modules first!
   module load IMAS-AL-Python IMAS-AL-Fortran iWrap XMLlib lxml
   python actor_install.py --skipModules grayscale.yml

   # Use -M with --skipModules to load a base module first
   python actor_install.py --skipModules -M IMAS-AL-Java grayscale.yml

   # Example: Loading modules for GENRAY actor
   module load IMAS-AL-Fortran/5.4.0-intel-2023b-DD-3.42.0
   module load XMLlib/3.3.2-intel-compilers-2023.2.1
   module load iWrap
   module load INTERPOS/9.2.0-iimkl-2023b
   module load netCDF-Fortran/4.6.1-iimpi-2023b
   python actor_install.py --skipModules genray.yml

   # Rebuild only (skip source checkout)
   python actor_install.py --skipModules --skipSources grayscale.yml

   # Install multiple actors
   python actor_install.py grayscale.yml toray.yml gray.yml

YAML Configuration File Format
-------------------------------

Each actor requires a YAML configuration file describing how to obtain, build, and install it.

File Structure
~~~~~~~~~~~~~~

.. code-block:: yaml

   ---
   SOURCES:
     - VCS: <version_control_system>
       REPO: <repository_url>
       VERSION: <branch_or_tag_or_hash>
       DIR: <local_directory_name>

   MODULES: [<module1>, <module2>, ...]

   BUILDS:
     - DIR: <directory>
       CMD: <build_command>

   ACTORS:
     - DIR: <directory>
       CMD: <install_command>

Section Descriptions
~~~~~~~~~~~~~~~~~~~~

SOURCES (Required)
^^^^^^^^^^^^^^^^^^

Defines where to obtain the source code.

**Fields:**

* ``VCS`` (string): Version control system - either ``git`` or ``svn``
* ``REPO`` (string): Repository URL (SSH or HTTPS)
* ``VERSION`` (string):
  
  * For **git**: branch name (e.g., ``develop``, ``master``), tag name (e.g., ``v1.0.0``), or full 40-character commit hash (e.g., ``89b416c9819b54156c2a92624b0f6424e06f7eec``)
  * For **svn**: revision number (e.g., ``r12345``)

* ``DIR`` (string): Local directory name where sources will be checked out

**Example (Git):**

.. code-block:: yaml

   SOURCES:
     - VCS: git
       REPO: ssh://git@git.iter.org/heat/grayscale.git
       VERSION: develop
       DIR: grayscale

**Example (SVN):**

.. code-block:: yaml

   SOURCES:
     - VCS: svn
       REPO: https://svn.example.org/actors/trunk
       VERSION: r12345
       DIR: my_actor

MODULES (Required)
^^^^^^^^^^^^^^^^^^

List of environment modules required for compilation and execution.

**Format:** YAML list of module names

**Example:**

.. code-block:: yaml

   MODULES: [IMAS-AL-Python, IMAS-AL-Fortran, iWrap, XMLlib, lxml]

**Common Modules:**

* ``IMAS-AL-Python`` - IMAS Access Layer for Python
* ``IMAS-AL-Fortran`` - IMAS Access Layer for Fortran
* ``iWrap`` - Actor wrapping tool
* ``XMLlib`` - XML parsing library
* ``lxml`` - Python XML library

BUILDS (Required)
^^^^^^^^^^^^^^^^^

Defines how to compile the actor libraries.

**Fields:**

* ``DIR`` (string): Directory where build command should be executed (usually same as source DIR)
* ``CMD`` (string): Shell command to execute for building

**Example:**

.. code-block:: yaml

   BUILDS:
     - DIR: grayscale
       CMD: make clean library FC=ifort DEBUG=yes

**Common Build Patterns:**

.. code-block:: yaml

   # Debug build with Intel Fortran
   CMD: make clean library FC=ifort DEBUG=yes

   # Optimized build
   CMD: make clean library FC=ifort

   # With specific flags
   CMD: make clean library FC=ifort FFLAGS="-O3 -fPIC"

   # Multiple targets
   CMD: make clean all install

ACTORS (Required)
^^^^^^^^^^^^^^^^^

Defines how to install/wrap the actor using iWrap or other tools.

**Fields:**

* ``DIR`` (string): Directory where installation command should be executed
* ``CMD`` (string or list): Shell command(s) to execute for actor installation

**Example (Single Command):**

.. code-block:: yaml

   ACTORS:
     - DIR: grayscale
       CMD: make clean iwrap_actor FC=ifort DEBUG=yes

**Example (Multiple Commands):**

.. code-block:: yaml

   ACTORS:
     - DIR: my_actor
       CMD:
         - make install_actor
         - python setup_actor.py
         - echo "Installation complete"

**Common Installation Patterns:**

.. code-block:: yaml

   # iWrap-based installation
   CMD: make clean iwrap_actor FC=ifort DEBUG=yes

   # Direct iWrap call with YAML config
   CMD: iwrap -f actor_config.yaml -i $ACTOR_FOLDER

   # Custom installation script
   CMD: python install_actor.py --prefix=$ACTOR_FOLDER

Complete Example
~~~~~~~~~~~~~~~~

Here's a complete example for the GRAYSCALE actor:

.. code-block:: yaml

   #example
   ---
   SOURCES:
     - VCS: git
       REPO: ssh://git@git.iter.org/heat/grayscale.git
       VERSION: develop
       DIR: grayscale

   MODULES: [IMAS-AL-Python, IMAS-AL-Fortran, iWrap, XMLlib, lxml]

   BUILDS: 
     - DIR: grayscale
       CMD: make clean library FC=ifort DEBUG=yes

   ACTORS: 
     - DIR: grayscale
       CMD: make clean iwrap_actor FC=ifort DEBUG=yes

   #COMMENTS:
   # This configuration builds the GRAYSCALE electron cyclotron actor
   # in debug mode using Intel Fortran compiler.

Workflow Steps
--------------

The script executes these steps in order:

1. **SETUP ENVIRONMENT** (unless ``--skipModules``)
   
   * Purges all loaded modules
   * Loads pre-module if specified with ``-M``
   * Loads all modules listed in ``MODULES`` section
   * Lists loaded modules for verification

2. **GET SOURCES** (unless ``--skipSources``)
   
   * Backs up existing directory if present (creates ``.DIR_BACKUP``)
   * Clones/checks out from repository
   * Verifies revision if ``--checkRevision`` is used

3. **BUILD LIBRARIES** (unless ``--skipBuilds``)
   
   * Changes to build directory
   * Executes build command
   * Reports success/failure

4. **INSTALL ACTORS** (unless ``--skipActors``)
   
   * Changes to actor directory
   * Executes installation command(s)
   * Reports success/failure

Environment Variables
---------------------

The script respects these environment variables:

* ``MODULESHOME`` - Location of Environment Modules installation
* ``LMOD_CMD`` - Location of Lmod command (alternative module system)
* ``FC`` - Fortran compiler (can be used in build commands)
* ``ACTOR_FOLDER`` - Destination for actor installation (if needed by install commands)

Module System Support
---------------------

The script automatically detects and works with:

* **Environment Modules** (traditional module system)
* **Lmod** (modern Lua-based module system)

Detection is performed by checking:

1. ``MODULESHOME`` environment variable
2. ``LMOD_CMD`` environment variable
3. Common installation paths
4. Shell function availability

Error Handling
--------------

* By default, errors in one YAML file don't stop processing of other files
* Use ``--pedantic`` to stop at first error
* Each step (MODULES, SOURCES, BUILDS, ACTORS) can be skipped if previous steps are complete
* Return codes indicate success (0) or failure (non-zero)

Output Files
------------

**RELEASE.yaml** - Generated after successful execution, contains:

* Timestamp and deployer information
* Module environment snapshot
* All executed steps and their parameters
* Useful for reproducing builds

Tips and Best Practices
------------------------

1. **Test with** ``--skipModules`` if modules are already loaded to save time
2. **Use** ``--skipSources`` when rebuilding without re-downloading
3. **Enable** ``--verbose`` for debugging build issues
4. **Keep DEBUG=yes** during development, remove for production builds
5. **Use absolute paths** when specifying custom directories
6. **Document special requirements** in YAML comments
7. **Version control your YAML files** to track configuration changes

Troubleshooting
---------------

Using --skipModules
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # When using --skipModules, you MUST load all required modules first
   # Check the MODULES section of your YAML file to see what's needed

   # Example for GRAYSCALE:
   module load IMAS-AL-Python IMAS-AL-Fortran iWrap XMLlib lxml
   python actor_install.py --skipModules grayscale.yml

   # To see what modules are currently loaded:
   module list

   # To find available versions:
   module avail IMAS-AL-Fortran
   module avail XMLlib

Module loading fails
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Pre-load required base module
   python actor_install.py -M IMAS-base grayscale.yml

Build fails with missing dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check that all required modules are in MODULES list
   # Verify module availability: module avail

Source checkout fails
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check SSH keys are configured for git repositories
   # Use --verbose to see detailed error messages

Actor installation fails
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Ensure ACTOR_FOLDER is set if needed
   export ACTOR_FOLDER=$HOME/my_actors
   export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH

Revision check fails with git branch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Error: "Wrong hash of cloned GIT repo, Got <hash> and was expecting develop"
   # This happens when using -R with a branch name
   
   # Solution 1: Don't use -R with branch names (it only works with commit hashes)
   python actor_install.py --skipModules grayscale.yml -D prasad
   
   # Solution 2: Use the full commit hash in your YAML file instead of branch name
   # In grayscale.yml, change:
   # VERSION: develop
   # To:
   # VERSION: 89b416c9819b54156c2a92624b0f6424e06f7eec
   
   # Solution 3: -R is mainly for production verification with fixed hashes
   # For development with branches, skip -R flag

Template
--------

Use this template to create configuration for new actors:

.. code-block:: yaml

   ---
   SOURCES:
     - VCS: git  # or svn
       REPO: <repository_url>
       VERSION: <branch_or_tag>
       DIR: <directory_name>

   MODULES: [IMAS-AL-Python, IMAS-AL-Fortran, iWrap, XMLlib, lxml]

   BUILDS:
     - DIR: <directory_name>
       CMD: make clean library FC=ifort

   ACTORS:
     - DIR: <directory_name>
       CMD: make clean iwrap_actor FC=ifort

   #COMMENTS:
   # Description of the actor
   # Special notes or requirements

See Also
--------

* IMAS Documentation: https://confluence.iter.org/display/IMP/
* iWrap Documentation: Available through ``module show iWrap``
* Available Actors: ``/work/imas/etc/modules/all``
