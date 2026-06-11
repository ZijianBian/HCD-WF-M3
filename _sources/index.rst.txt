HCD Workflow Documentation
==========================

Welcome to the HCD (Heating and Current Drive) Workflow documentation for ITER
plasma simulations.

The HCD Workflow is a Python-based workflow management system designed to
orchestrate various heating and current drive simulation codes for ITER tokamak
plasma physics analysis.

Start Here
----------

If you only read three pages, read these:

* :doc:`user/quickstart`
* :doc:`user/execution_modes`
* :doc:`user/validation`

Current Status
--------------

HCD Workflow has three execution modes.

.. list-table::
   :header-rows: 1
   :widths: 18 28 54

   * - Mode
     - Entry point
     - Status
   * - Legacy
     - ``workflow/workflow_driver.py`` with ``m3_flag=0``
     - Stable in-process iWrap workflow.
   * - Hybrid M3
     - ``workflow/workflow_driver.py`` with ``m3_flag=1``
     - Stable two-component MUSCLE3 coupling. The micro component still runs
       iWrap actors internally.
   * - Pure M3
     - ``hcdworkflow/workflow_driver_m3_pure.py``
     - Experimental but runnable for the validated Pure M3 subset:
       Torbeam, Cyrano, merge_waves, and hcd2core_sources without FoPla.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user/quickstart
   user/execution_modes
   user/usage
   user/validation
   user/inspecting_results
   user/installation
   user/gui
   user/examples

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer/setup
   developer/architecture
   developer/pure_m3
   developer/troubleshooting
   developer/actor_installation
   developer/contributing
   developer/api

.. toctree::
   :maxdepth: 1
   :caption: Reference

   reference/configuration
   reference/commands
   reference/actors
   reference/available_modules

Generated HTML
--------------

The documentation source is under ``docs/source``. The generated site is under
``docs/build/html`` and should not be edited by hand.

To rebuild:

.. code-block:: bash

   cd docs
   ../devenv/bin/python -m sphinx -M html source build
