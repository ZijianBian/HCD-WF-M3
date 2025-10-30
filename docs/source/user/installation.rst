Installation
============

For Users (EasyBuild Module)
-----------------------------

The easiest way to use HCD Workflow is through the pre-installed EasyBuild module on ITER HPC systems.

Prerequisites
~~~~~~~~~~~~~

* Access to ITER HPC cluster
* Basic familiarity with Linux commands and module system

Loading the Module
~~~~~~~~~~~~~~~~~~

Load the workflow module:

.. code-block:: bash

   module load HCD-WF

Following Actor Modules will be automaticall loaded
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Mandatory Actors:**

.. code-block:: bash

   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0

**EC Heating Actors:**

.. code-block:: bash

   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load GRAY/1.0.0-intel-2023b-DD-3.42.0
   module load TORBEAM/3.8.0-intel-2023b-DD-3.42.0
   module load TORAY/1.0.0-intel-2023b-DD-3.42.0
   module load GENRAY/10.11.3-intel-2023b-DD-3.42.0

**IC Heating Actors:**

.. code-block:: bash

   module load CYRANO/1.0.0-intel-2023b-DD-3.42.0
   module load FoPla/2.1.0-intel-2023b-DD-3.42.0
   module load StixReDist/2.1.0-intel-2023b-DD-3.42.0
   module load TOMCAT/1.0.0-intel-2023b-DD-3.42.0

**NBI Actors:**

.. code-block:: bash

   module load NEMO/2.2.0-intel-2023b-DD-3.42.0
   module load NBISIM/1.3.0-intel-2023b-DD-3.42.0
   module load RISK/2.2.0-intel-2023b-DD-3.42.0
   module load SPOT/2.4.0-intel-2023b-DD-3.42.0

**Other Actors:**

.. code-block:: bash

   module load RELAX/1.0.0-intel-2023b-DD-3.42.0
   module load SMART/0.1.0-intel-2023b-DD-3.42.0
   module load FPSIM/1.0.0-intel-2023b-DD-3.42.0


This will automatically load:

* Python environment
* IMAS-AL-Python
* matplotlib
* Tkinter
* All HCD workflow commands (``hcd_gui``, ``hcd_nogui``, ``hcd_batch``, ``hcdslice_nogui``)

Verify Installation
~~~~~~~~~~~~~~~~~~~

Check that the commands are available:

.. code-block:: bash

   which hcd_nogui
   hcd_nogui --help

   which hcd_gui
   hcd_gui --help

Optional: Suppress IMAS Warnings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To reduce verbose output, you can set:

.. code-block:: bash

   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

For Developers (Python Environment)
------------------------------------

If you need to develop or modify HCD Workflow, install from source.

Prerequisites
~~~~~~~~~~~~~

* Python 3.8 or higher
* Git
* Access to ITER git repository

Clone the Repository
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone ssh://git@git.iter.org/wf/hcd-wf.git
   cd hcd-wf

Checkout the Desired Branch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For production use:

.. code-block:: bash

   git checkout release/<tag name> # 2.4.0
   git pull

For development:

.. code-block:: bash

   git fetch
   git checkout develop

Setup Python Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   module load Python
   python -m venv devenv
   source devenv/bin/activate

Install HCD Workflow
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install -e .

Load Required IMAS Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   module load Tkinter              # For GUI support
   module load matplotlib           # For plotting
   module load waveform-cooker
   module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0

Load Actor Modules
~~~~~~~~~~~~~~~~~~

Load the actors you need for your workflow. Available at :

.. code-block:: bash

   # Mandatory actors
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0
   
   # EC heating actors (load as needed)
   module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
   module load GRAY/1.0.0-intel-2023b-DD-3.42.0
   module load TORBEAM/3.8.0-intel-2023b-DD-3.42.0
   module load TORAY/1.0.0-intel-2023b-DD-3.42.0
   module load GENRAY/10.11.3-intel-2023b-DD-3.42.0
   
   # IC heating actors (load as needed)
   module load CYRANO/1.0.0-intel-2023b-DD-3.42.0
   module load FoPla/2.1.0-intel-2023b-DD-3.42.0
   module load StixReDist/2.1.0-intel-2023b-DD-3.42.0
   module load TOMCAT/1.0.0-intel-2023b-DD-3.42.0
   
   # NBI actors (load as needed)
   module load NEMO/2.2.0-intel-2023b-DD-3.42.0
   module load NBISIM/1.3.0-intel-2023b-DD-3.42.0
   module load RISK/2.2.0-intel-2023b-DD-3.42.0
   module load SPOT/2.4.0-intel-2023b-DD-3.42.0
   
   # Other actors
   module load RELAX/1.0.0-intel-2023b-DD-3.42.0
   module load SMART/0.1.0-intel-2023b-DD-3.42.0
   module load FPSIM/1.0.0-intel-2023b-DD-3.42.0

Verify Installation
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   which hcd_gui
   hcd_gui

Uninstall and Reinstall
~~~~~~~~~~~~~~~~~~~~~~~~

If you need to reinstall after code changes:

.. code-block:: bash

   pip uninstall hcdworkflow
   pip install .

Dependencies
------------

The following Python packages are installed automatically:

* lxml >= 4.6.0
* numpy >= 1.20.0
* pyparsing >= 2.4.0
* python-dateutil >= 2.8.0
* pyyaml >= 5.4.0
* six >= 1.15.0

Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~

**Documentation Building:**

.. code-block:: bash

   pip install -e ".[docs]"

This installs:

* sphinx >= 5.0
* sphinx-rtd-theme >= 1.0

**Development and Testing:**

.. code-block:: bash

   pip install -e ".[dev]"

This installs additional tools:

* pytest >= 7.0
* pytest-cov >= 4.0
* pylint >= 2.0
* black >= 22.0
* flake8 >= 5.0
* sphinx >= 5.0 (for documentation)
* sphinx-rtd-theme >= 1.0 (for documentation)

**Testing Only:**

.. code-block:: bash

   pip install -e ".[test]"

This installs:

* pytest >= 7.0
* pytest-cov >= 4.0

**Actor Installation:**

.. code-block:: bash

   pip install -e ".[actors]"

This installs dependencies for building actors from source:

* pyyaml >= 5.1

Troubleshooting
---------------

Module Not Found
~~~~~~~~~~~~~~~~

If you get "module not found" errors, ensure you have sourced your virtual environment:

.. code-block:: bash

   source devenv/bin/activate

Import Errors
~~~~~~~~~~~~~

If IMAS modules are not found, ensure you've loaded the required modules:

.. code-block:: bash

   module list  # Check loaded modules
   module av IMAS  # List available IMAS modules

Permission Errors
~~~~~~~~~~~~~~~~~

If you encounter permission errors during installation, ensure you're in a virtual environment and not trying to install system-wide.
