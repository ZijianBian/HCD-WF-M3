"""Selection of the configuration files of a workflow configuration folder.

A configuration file ``<name>.<ext>`` (``input_workflow.xml``, an actor code-parameter file
``input_<actor>.xml``, a waveform file ``<system>_waveforms.yaml``) holds the content for Data Dictionary 4
and may have variants in the same folder:

- ``<name>_dd3.<ext>``: the content for a DD 3 environment, only for files whose content depends on the DD;
- ``<name>_reg.<ext>``: the regression variant, with degraded, faster settings for the regression tests
  (``ci-sdcc/st03-regression.sh``), read only when the environment variable ``HCDWF_TEST_MODE`` is ``1``
  (or ``true``);
- ``<name>_reg_dd3.<ext>``: the regression variant of a DD-dependent file for a DD 3 environment.

The first existing file of this list is read: ``<name>_reg_dd3`` (regression mode, DD 3), ``<name>_dd3``
(DD 3), ``<name>_reg`` (regression mode), ``<name>``. The DD is the target DD of the workflow
(``IMAS_VERSION``, else the DD of the loaded IMAS-Fortran module).
"""

import os

TEST_MODE_VARIABLE = "HCDWF_TEST_MODE"
REGRESSION_SUFFIX = "_reg"
DD3_SUFFIX = "_dd3"

_reported = set()


def regression_mode() -> bool:
    """Return True when the regression variants of the configuration files are selected."""
    return os.environ.get(TEST_MODE_VARIABLE, "").strip().lower() in ("1", "true")


def target_dd_major() -> str:
    """Major version of the target DD of the workflow, e.g. "4"."""
    from workflow.ids_prep import _get_target_dd_version

    return _get_target_dd_version().split(".", 1)[0]


def candidates(path: str) -> list[str]:
    """Return the files read for ``path``, in the order in which they are searched."""
    stem, extension = os.path.splitext(path)
    is_dd3 = target_dd_major() == "3"
    suffixes = []
    if regression_mode() and is_dd3:
        suffixes.append(REGRESSION_SUFFIX + DD3_SUFFIX)
    if is_dd3:
        suffixes.append(DD3_SUFFIX)
    if regression_mode():
        suffixes.append(REGRESSION_SUFFIX)
    return [f"{stem}{suffix}{extension}" for suffix in suffixes] + [path]


def config_file(path: str, report: bool = True) -> str:
    """Return the configuration file to read for ``path``: the first existing file of candidates(path),
    else ``path``. The choice is printed once per file when ``report`` is True.
    """
    chosen = next((candidate for candidate in candidates(path) if os.path.exists(candidate)), path)
    if report and chosen not in _reported:
        _reported.add(chosen)
        mode = f"{TEST_MODE_VARIABLE}=1" if regression_mode() else "normal mode"
        print(f"[hcdworkflow] Configuration file ({mode}, DD {target_dd_major()}): {chosen}", flush=True)
    return chosen
