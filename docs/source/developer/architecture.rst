Architecture
============

HCD-WF reads IMAS slices, prepares heating inputs, runs the selected physics
actors and stores their outputs. The execution mode changes where those
steps run. See :doc:`../user/execution_modes` for choosing and launching a
mode.

Drivers and data flow
---------------------

.. code-block:: text

   Legacy: workflow_driver -> HCDWorkflow -> iWrap actors
   Hybrid: workflow_driver <-> hcd_workflow_m3 -> HCDWorkflow -> iWrap actors
   Pure:   workflow_driver_m3_pure <-> native MUSCLE3 actors

The two standalone drivers own database access and the time loop.
``setup_databases()`` reads the workflow configuration, opens input/output
databases and prepares a machine-description database from input IDSs and
waveforms. ``get_ids_slices()`` reads each time slice;
``store_ids_slices()`` writes the prepared inputs and available outputs.
These functions live in ``workflow/workflow_driver.py`` and are shared
with the Pure driver.

MUSCLE3 exchanges stop on IDS serialization or deserialization errors.
Drivers reject returned message timestamps that differ from the requested
slice by more than ``1e-9`` seconds or are not finite.

In Legacy and Hybrid, ``HCDWorkflow.initialize()`` creates ``WorkflowData``
from the configuration directory. For each slice, ``setProcessStatus()``
selects active processes and ``run()`` delegates to ``WorkflowExecutor``.
The executor resolves the configured algorithm, actor inputs and mergers.
``HCDWorkflow`` itself does not open the scenario databases.

``workflow/ids_prep.py`` contains shared DD conversion, IDS preparation
and output-shape handling. Configuration parsing belongs to
``workflow_config_reader.py``; actor registrations and dependency lists
come from ``hcdworkflow/global_configuration/global_lists.yaml``.

Preparing a launch
------------------

``gui/launch_config.py`` serves both the GUI and ``run.sh``. It copies a
topology template into a run directory, binds it to the saved configuration
and resolves driver and actor-parameter paths. Pure launch keeps the actors
selected in ``input_workflow.xml``. A custom topology must provide every
selected actor. MUSCLE3 Manager starts the checked, generated yMMSL file.

The topology defines components, ports and connections; it does not by
itself make independent actors run concurrently. The driver's send/receive
order determines when each connected actor can start.

.. _hybrid-clock-contract:

Hybrid clock contract
---------------------

The macro sends one serialized IDS per connected ``O_I`` port and receives
outputs on ``S`` ports. The ``hcd_workflow_m3.py`` micro receives inputs on
``F_INIT`` and returns outputs on ``O_F``. One macro reuse contains the
standalone time loop; each exchange invokes one micro reuse.

When the micro is embedded in a Plasma Discharge Simulator (PDS), the outer
controller supplies its clock. The same rules apply to messages from the
standalone macro:

* All connected input timestamps must agree within ``1e-9`` seconds, with
  no relative tolerance, and the timestamp must be finite.
* XML ``tbegin`` and ``tend`` must be finite. Nonnegative bounds constrain
  the incoming time with the same tolerance. Negative bounds impose no
  constraint in the micro, which has no database from which to infer them.
* ``one_time_slice`` does not limit the micro's reuse loop. The controller
  decides how many slices to send.
* Outputs use the accepted input timestamp and preserve the first
  connected input's ``next_timestamp``. The micro neither compares all
  ``next_timestamp`` values nor imposes a future-time rule on that value.

A clock violation stops the micro through MUSCLE3 error shutdown. Process
activation uses the accepted controller time; homogeneous single-slice
output IDSs are stamped with that time before serialization.

.. _pure-m3-scheduling:

Pure actor scheduling
---------------------

``hcdworkflow/workflow_driver_m3_pure.py`` maps actor ports in
``ACTOR_PORTS`` and exchanges IDSs directly with the connected native
executables. It does not call ``HCDWorkflow.run()``. The default order is
Torbeam, Cyrano, wave merging, an optional fast-particle actor, then
``hcd2core_sources``.

Connected Torbeam runs on every slice. Cyrano and FoPla run only when the
absolute IC launched power exceeds ``1e-6 W``. Wave merging requires both
positive EC power above that threshold and active IC power; otherwise the
driver carries forward the applicable wave branch. FoPla receives the IC
waves, while post-processing receives the combined waves.

Rabbit runs after the wave calculation and advances on every slice,
including zero-NBI-power slices, to preserve its state. Its topology must
agree with ``nbi_fp=1``. Rabbit and FoPla cannot be connected together:
the driver does not implement merging their distribution outputs.

Optional EC/IC concurrency
~~~~~~~~~~~~~~~~~~~~~~~~~~

The yMMSL setting ``pure_parallel_ec_ic: true`` makes the driver send both
Torbeam and Cyrano inputs before receiving their results. Their native
processes can then compute concurrently; all Python ``Instance`` calls
remain on one thread. The setting defaults to ``false``.

This requires Torbeam and Cyrano, with only ``merge_waves`` and
``hcd2core_sources`` allowed as additional actors. Rabbit and FoPla are
excluded. Cyrano must not depend on Torbeam's output: its XML must contain
one finite value for each of the following parameters:

* ``Ntor != 0`` and ``frequency > 0``;
* ``total_power == 1`` (antenna power) or ``total_power > 2`` (explicit power);
* ``include_nbi == include_fasticrh == include_alphas == 0``.

The driver checks these conditions before running. In this schedule,
Cyrano receives an empty waves input, then the two wave outputs are merged
after both actors finish. The serial schedule retains the EC-to-IC waves
input.

Extending the workflow
----------------------

For an iWrap actor, update the actor registration and dependencies used by
``WorkflowData`` and ``WorkflowExecutor``. For a native Pure actor, update
the port registry, topology, launch validation and driver schedule together.
In both cases, verify the actor's IDS and time contract before comparing a
single slice and then a multi-slice run. :doc:`api` identifies the relevant
entry points; :doc:`actor_installation` covers the external builds.
