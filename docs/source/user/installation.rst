Installation
============

What is HCD Workflow?
---------------------
HCD Workflow is a Python-based system for orchestrating plasma heating and current drive simulations on HPC systems. It provides both command-line and GUI tools for running, testing, and developing simulation workflows.

Quick Start (For Users)
-----------------------
If you just want to run simulations on the HPC cluster:
For step-by-step instructions on using the GUI and creating configuration, see :doc:`gui`.

.. code-block:: bash

   module load HCD-WF
   hcd_nogui -c <config_folder>   # Run a simulation
   hcd_gui                       # Launch the GUI

This loads all required dependencies and actors automatically. No manual module loading is needed for standard use.

Creating a Configuration Folder via the GUI
-------------------------------------------

You can create a new configuration folder directly from the HCD Workflow GUI:
For a detailed guide to using the GUI, see :doc:`gui`.

1. Launch the GUI:

   .. code-block:: bash

      hcd_gui

2. In the GUI, set up your simulation parameters as needed.

3. Click the **Save** button (usually located in the toolbar or under the "File" menu).

4. When prompted, choose a location and name for your configuration folder. The GUI will create the folder and save all necessary configuration files inside it.

This configuration folder can then be used for running simulations from the command line:

.. code-block:: bash

   hcd_nogui -c <your_config_folder>

Troubleshooting (Common Issues)
-------------------------------
- **Command not found**: Make sure you loaded the module and are on a login node.
- **Module import errors**: Ensure all required modules are loaded (see below).
- **Permission errors**: Make sure you are using a virtual environment and not installing system-wide.

For Users (Details)
-------------------

Prerequisites
~~~~~~~~~~~~~
* Access to HPC cluster
* Basic familiarity with Linux commands and module system

Loading the Module
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   module load HCD-WF

This will automatically load:

* Python environment
* IMAS-AL-Python
* matplotlib
* Tkinter
* All HCD workflow commands (``hcd_gui``, ``hcd_nogui``, ``hcd_batch``, ``hcdslice_nogui``)
* All required actor modules (see below for advanced/optional details)

**Optional: Suppress IMAS Warnings**

.. code-block:: bash

   export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1


Verify Installation
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   which hcd_nogui
   hcd_nogui --help
   which hcd_gui
   hcd_gui --help

---

For Developers (Source Installation)
------------------------------------
If you want to develop or modify HCD Workflow, install from source. On ITER SDCC, you can use the helper script:

.. code-block:: bash

   ./config_hcd_iter_sdcc.sh

Set ``ACTOR_FOLDER`` to point to a directory of locally compiled actors (created with ``actor_install.py``) if you want to work with custom builds:

.. code-block:: bash

   ACTOR_FOLDER=~/actors/local ./config_hcd_iter_sdcc.sh 3.42.0

Manual Developer Setup
~~~~~~~~~~~~~~~~~~~~~~

Prerequisites
^^^^^^^^^^^^^
* Python 3.8 or higher
* Git
* Access to ITER git repository

Clone the Repository
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git clone ssh://git@git.iter.org/wf/hcd-wf.git
   cd hcd-wf

Checkout the Desired Branch
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git checkout develop   # for development
   git checkout release/<tag name>  # for production
   git pull

Setup Python Virtual Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   module load Python
   python -m venv devenv
   source devenv/bin/activate

Install HCD Workflow
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install -e .

Load Required IMAS and Actor Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   module load Tkinter matplotlib waveform-cooker IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
   # Load actor modules as needed (see above)

---

load specific actor modules (for custom workflows or debugging):

.. code-block:: bash

   # Mandatory actors
   module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
   module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0
   # EC, IC, NBI, and other actors as needed (see project docs)

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

* sphinx < 8.0
* sphinx-immaterial >= 0.13

**Development and Testing:**

.. code-block:: bash

   pip install -e ".[dev]"

This installs additional tools:

* pytest >= 7.0
* pytest-cov >= 4.0
* pylint >= 2.0
* black >= 22.0
* flake8 >= 5.0
* sphinx < 8.0 (for documentation)
* sphinx-immaterial >= 0.13 (for documentation)

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

---

What Next?
-----------
- See the user guide for running your first simulation and example configurations.
- For advanced configuration, see the documentation or ask the HCD Workflow team for help.
- If you encounter issues, check the troubleshooting section above or contact support.
