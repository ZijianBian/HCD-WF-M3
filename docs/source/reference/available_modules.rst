Available Modules
=================

Use the project environment helper first:

.. code-block:: bash

   source config_hcd_iter_sdcc.sh

Manual module loading is mainly for debugging or reproducing an older setup.

Check Modules
-------------

.. code-block:: bash

   module avail HCD
   module avail MUSCLE3
   module avail TORBEAM
   module avail FoPla
   module avail IDStools
   module list

IDS Inspection
--------------

Use IDStools or IMAS-Python scripts to inspect completed IMAS runs. The exact
database, backend, shot, and run come from ``input_workflow.xml``.

Legacy Stack
------------

For DD 3.42.0 compatibility work, use:

.. code-block:: bash

   source config_hcd_iter_sdcc_3.42.0.sh

Do not mix the DD 3.42.0 environment and the current DD 4.1.0 ``devenv`` in the
same shell.
