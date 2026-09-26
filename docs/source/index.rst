H&CD Workflow Handbook
======================

Welcome to the HCD (Heating and Current Drive) Workflow documentation for ITER
plasma simulations.

The HCD Workflow is a Python-based workflow management system designed to
orchestrate heating and current-drive simulation codes for ITER tokamak plasma
physics analysis.

Start with :doc:`user/quickstart` for a first run. Use
:doc:`user/execution_modes` to choose how the actors are launched, or
:doc:`user/gui` to prepare a configuration interactively.

This handbook describes the source checkout containing ``run.sh`` and the
``topologies/`` templates. An installed HCD-WF module may provide an earlier
release; see :doc:`user/installation`.

.. toctree::
   :maxdepth: 1
   :caption: Running a workflow

   user/quickstart
   user/execution_modes
   user/gui
   user/usage
   user/examples
   user/validation
   user/installation

.. toctree::
   :maxdepth: 1
   :caption: Reference

   reference/configuration
   reference/commands
   reference/actors
   reference/available_modules

.. toctree::
   :maxdepth: 1
   :caption: Development

   developer/setup
   developer/architecture
   developer/actor_installation
   developer/contributing
   developer/api
