Checking a result
=================

A workflow can finish with missing slices or actor warnings. Before using a
result, check the stored data and numerical diagnostics of the selected actors.

Start with the output IMAS entry:

* Are the requested time slices present?
* Do the expected heating systems and source profiles appear?
* Are their grids, units and power conventions appropriate for the case?
* Do the actor logs report convergence failures or invalid numerical values?

Then check the quantities relevant to your calculation, such as integrated
deposited power, particle inventory or driven current, against the prescribed
inputs and the actor's numerical tolerances. A mode or topology name alone
does not establish physical convergence.

When comparing Legacy, Hybrid and Pure, hold the input data, actor versions,
parameters and time range fixed. Compare the resulting IDSs before comparing
elapsed time. Different wrappers need not produce bitwise-identical arrays.

The relevant logs and output locations are described in :doc:`usage`.
