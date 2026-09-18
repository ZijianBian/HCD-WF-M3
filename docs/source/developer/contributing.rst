Contributing
============

The repository's `CONTRIBUTING.md
<https://github.com/iterorganization/HCD-WF/blob/develop/CONTRIBUTING.md>`_
defines the contribution process, including discussing proposed changes
and creating a feature branch from ``develop``. Follow that document for
project policy.

Keep each change focused enough for a reviewer to explain its effect.
Describe the behavior before and after the change, the checks you ran and
any remaining limitation. Update the handbook page where a reader first
encounters the changed behavior.

For documentation, give the reader one working path before presenting
alternatives. Prefer a short explanation and a concrete command to repeated
option lists. Keep detailed contracts in the reference or developer pages
and link to them from the user guide. Build the handbook as described in
:doc:`setup` and read the rendered page before submitting it.

Keep personal environments, generated HTML, run data, logs and local
diagnostic scripts out of the proposed change. Physics verification may
require local runs; summarize the relevant outcome in the review description
without adding their output directories to the source tree.
