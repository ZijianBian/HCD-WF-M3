Developer Setup
===============

This guide is for developers who want to contribute to or modify the HCD Workflow codebase.

Prerequisites
-------------

* Python 3.8 or higher
* Git
* Access to ITER git repository
* Familiarity with Python development
* Basic knowledge of IMAS (Integrated Modelling & Analysis Suite)

Getting the Source Code
------------------------

Clone the Repository
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   mkdir ~/hcdwfrepo # or create folder of your choice
   cd hcdwfrepo
   git clone ssh://git@git.iter.org/wf/hcd-wf.git
   cd hcd-wf

Check Available Branches
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git branch -a
   git fetch

Checkout Development Branch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git checkout develop
   git pull

Or checkout a specific release:

.. code-block:: bash

   git checkout release/<tag name> # 2.4.0
   git pull

Setting Up Development Environment
-----------------------------------

.. tip::

   On ITER SDCC systems you can automate most of the steps below with the
   :file:`config_hcd_iter_sdcc.sh` helper that ships at the root of the
   repository. Running::

      ./config_hcd_iter_sdcc.sh

   loads the standard HCD-WF module stack, creates the ``devenv`` virtual
   environment, and installs the project in editable mode. Set the
   ``ACTOR_FOLDER`` environment variable to point at a directory created by
   ``actor_install.py`` if you prefer to develop against locally built
   actors::

      ACTOR_FOLDER=~/actors/local ./config_hcd_iter_sdcc.sh 3.42.0

   The manual instructions below remain available if you need finer control.

Load Required Modules
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   module load Python
   module load Tkinter          # For GUI development
   module load matplotlib       # For plotting
   module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0

Create Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python -m venv devenv
   source devenv/bin/activate

Install in Editable Mode
~~~~~~~~~~~~~~~~~~~~~~~~~

For development, install in editable mode so changes are immediately reflected:

.. code-block:: bash

   pip install -e .

Install Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install -e ".[dev]"

This installs:

* pytest >= 7.0
* pytest-cov >= 4.0
* pylint >= 2.0
* black >= 22.0
* flake8 >= 5.0

Load Actor Modules
~~~~~~~~~~~~~~~~~~

Load the actors you need for testing on SDCC. :

.. code-block:: bash

   # Mandatory actors
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0
   
   # EC heating actors
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load GRAY/1.0.0-intel-2023b-DD-3.42.0
   module load TORBEAM/3.8.0-intel-2023b-DD-3.42.0
   module load TORAY/1.0.0-intel-2023b-DD-3.42.0
   module load GENRAY/10.11.3-intel-2023b-DD-3.42.0
   
   # IC heating actors
   module load CYRANO/1.0.0-intel-2023b-DD-3.42.0
   module load FoPla/2.1.0-intel-2023b-DD-3.42.0
   module load StixReDist/2.1.0-intel-2023b-DD-3.42.0
   module load TOMCAT/1.0.0-intel-2023b-DD-3.42.0
   
   # NBI actors
   module load NEMO/2.2.0-intel-2023b-DD-3.42.0
   module load NBISIM/1.3.0-intel-2023b-DD-3.42.0
   module load RISK/2.2.0-intel-2023b-DD-3.42.0
   module load SPOT/2.4.0-intel-2023b-DD-3.42.0
   
   # Other actors
   module load RELAX/1.0.0-intel-2023b-DD-3.42.0
   module load SMART/0.1.0-intel-2023b-DD-3.42.0
   module load FPSIM/1.0.0-intel-2023b-DD-3.42.0

**Note**: You only need to load the actors you plan to use in your workflow.

Set Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1
   export PYTHONPATH=$PWD:$PYTHONPATH

Installing Custom Actors
-------------------------

Prerequisites: Request Repository Access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before you can compile actors, you must request access to their GIT repositories:

1. Go to `IMAS S/W Repository Access <https://jira.iter.org/servicedesk/customer/portal/1/create/257>`_
2. Fill out the form for each repository you need access to
3. See :doc:`../reference/actors` for complete list of available actors and repositories

**Minimum Recommended Access:**

* HCD WF (the workflow itself)
* HCD Mergers (mandatory)
* Waveform Cooker (highly recommended)
* At least one heating source actor (EC, IC, or NBI)

Method 1: Compile All Actors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have access to all actor repositories:

.. code-block:: bash

   cd actor_install
   
   # Compile all actors with .yml files
   python actor_install.py *.yml --SkipModules

**Note**: If you don't have access to all repositories, remove the ``.yml`` files for actors you cannot access, otherwise the script will fail.

Method 2: Compile Specific Actors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compile only the actors you need:

.. code-block:: bash

   cd actor_install
   
   # Compile GRAYSCALE
   python actor_install.py grayscale.yml --SkipModules
   
   # Compile NEMO
   python actor_install.py nemo.yml --SkipModules
   
   # Compile HCD mergers (mandatory)
   python actor_install.py hcd_mergers.yml --SkipModules

Method 3: Copy Pre-compiled Actors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For testing actors under development:

Setup Actor Folder
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export ACTOR_FOLDER=~/development/actors
   mkdir -p $ACTOR_FOLDER
   export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH

Using actor_install Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``actor_install/`` folder contains scripts and configuration for building actors:

.. code-block:: bash

   cd actor_install
   
   # Install all actors
   python actor_install.py --skipModules *.yml
   
   # Install specific actor
   python actor_install.py --skipModules ascot.yml
   python actor_install.py --skipModules grayscale.yml

Update Existing Actor
~~~~~~~~~~~~~~~~~~~~~

When an actor is updated:

.. code-block:: bash

   cd actor_install
   python actor_install.py --skipModules <actor>.yml

The build artifacts are in ``build-<DATE>-<TIME>`` folders.


Development Workflow
--------------------

Making Changes
~~~~~~~~~~~~~~

1. Create a feature branch:

   .. code-block:: bash

      git checkout -b feature/my-new-feature

2. Make your changes

3. Test your changes:

   .. code-block:: bash

      hcdslice_nogui -c tests/data/GRAYSCALE/

4. Run code quality checks:

   .. code-block:: bash

      black hcdworkflow/
      flake8 hcdworkflow/
      pylint hcdworkflow/

Running and Writing Tests with Pytest
-------------------------------------

Automated integration tests are provided using pytest. These tests run the main workflow commands for various configurations and check for successful completion.

**Install pytest (if not already installed):**

.. code-block:: bash

   pip install pytest

**Run all workflow tests:**

.. code-block:: bash

   pytest tests/test_workflow.py

Or run all tests in the directory:

.. code-block:: bash

   pytest tests/

**Writing new tests:**

- Add new test functions to `tests/test_workflow.py` or create new files in the `tests/` directory.
- Use `subprocess.run` to invoke CLI commands and assert on their return codes and output.
- See the existing test file for examples.

Running Tests
~~~~~~~~~~~~~

Currently the project has test data but no automated tests. To test:

.. code-block:: bash

   # Test console mode
   hcd_nogui -c tests/data/GRAYSCALE/
   
   # Test single slice
   hcdslice_nogui -c tests/data/GRAYSCALE/
   
   # Test GUI
   hcd_gui

Code Quality
~~~~~~~~~~~~

Run static analysis as done in CI:

.. code-block:: bash

   # From project root
   bash ci-sdcc/st05-staticanalysis.sh

Or manually:

.. code-block:: bash

   # Format code
   black --line-length 120 hcdworkflow/ gui/ tools/ workflow/
   
   # Check code style
   flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow/
   
   # Run pylint
   pylint --max-line-length=120 --disable=E0401 -E ./hcdworkflow/*.py
   
   # Check with ruff
   ruff check hcdworkflow --select F401,E402

Reinstalling After Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you installed with ``pip install -e .``, changes are automatically picked up. Otherwise:

.. code-block:: bash

   pip uninstall hcdworkflow
   pip install .

Configuration Files
-------------------

Important configuration files in the project:

pyproject.toml
~~~~~~~~~~~~~~

Modern Python project configuration:

* Project metadata
* Dependencies
* Build system
* Tool configurations (black, pytest)

setup.cfg
~~~~~~~~~

Legacy configuration for:

* flake8
* pylint  
* ruff
* pytest

.pylintrc
~~~~~~~~~

Detailed pylint configuration optimized for scientific code.

.git-blame-ignore-revs
~~~~~~~~~~~~~~~~~~~~~~

Git blame ignore file for formatting commits.

Debugging
---------

Enable Verbose Output
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   unset IMAS_AL_DISABLE_OBSOLESCENT_WARNING

Use Python Debugger
~~~~~~~~~~~~~~~~~~~

Add breakpoints in code:

.. code-block:: python

   import pdb; pdb.set_trace()

Or use IDE debugger with the command-line arguments.

Check Logs
~~~~~~~~~~

Actor logs are saved when configured:

.. code-block:: python

   parameters[code + "_log"] = "path/to/logfile.log"

Print Debug Info
~~~~~~~~~~~~~~~~

Add strategic print statements:

.. code-block:: python

   print("DEBUG:", variable_name, file=sys.stderr)

Building Distribution
---------------------

Build Wheel Package
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python -m build

This creates:

* ``dist/HCDWorkflow-<version>-py3-none-any.whl``
* ``dist/HCDWorkflow-<version>.tar.gz``

Install Built Package
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install dist/HCDWorkflow-<version>-py3-none-any.whl

Version Management
------------------

The project uses ``setuptools_scm`` for automatic versioning from git tags.

Version is automatically written to:

.. code-block:: bash

   hcdworkflow/_version.py

To see current version:

.. code-block:: python

   from hcdworkflow._version import version
   print(version)

Common Development Tasks
------------------------

Add New Actor
~~~~~~~~~~~~~

1. Create ``actor_install/<actor>.yml`` configuration
2. Run ``python actor_install/actor_install.py --skipModules <actor>.yml``
3. Add to ``global_lists.yaml`` if needed
4. Test integration

Troubleshooting Development Issues
-----------------------------------

Import Errors
~~~~~~~~~~~~~

* Ensure virtual environment is activated
* Check ``PYTHONPATH`` includes project root
* Verify modules are loaded

Module Not Found After Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Reinstall: ``pip uninstall hcdworkflow && pip install -e .``
* Check installation: ``pip show hcdworkflow``
* Verify command location: ``which hcd_nogui``

Git Issues
~~~~~~~~~~

* Ensure SSH keys are configured for ITER git
* Check branch status: ``git status``
* Update remotes: ``git fetch``

Best Practices
--------------

1. **Use Editable Install**: Always use ``pip install -e .`` during development
2. **Test Before Commit**: Run ``hcdslice_nogui`` on test cases
3. **Follow Style Guide**: Run black and flake8 before committing
4. **Document Changes**: Update relevant ``.rst`` files
5. **Use Feature Branches**: Never commit directly to ``develop`` or ``main``
6. **Write Commit Messages**: Clear, descriptive commit messages
7. **Keep Dependencies Updated**: Regularly update ``pyproject.toml``

See Also
--------

* :doc:`architecture` - Understanding the codebase
* :doc:`contributing` - Contribution guidelines
* :doc:`api` - API documentation
