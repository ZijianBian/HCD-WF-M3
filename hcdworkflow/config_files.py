"""Selection of the configuration files of a workflow configuration folder.

When the environment variable ``HCDWF_TEST_MODE`` is ``1`` (or ``true``), a configuration file
``<name>.xml`` is replaced by its regression variant ``<name>_reg.xml`` from the same folder when
that file exists; otherwise the normal file is used. The regression variants hold degraded, faster
settings for the regression tests (``ci-sdcc/st03-regression.sh``) and are never used by default.
"""

import os

TEST_MODE_VARIABLE = "HCDWF_TEST_MODE"
REGRESSION_SUFFIX = "_reg"

_reported = set()


def regression_mode() -> bool:
    """Return True when the regression variants of the configuration files are selected."""
    return os.environ.get(TEST_MODE_VARIABLE, "").strip().lower() in ("1", "true")


def regression_variant(path: str) -> str:
    """Return the path of the regression variant of a configuration file: ``<stem>_reg<ext>``."""
    stem, extension = os.path.splitext(path)
    return f"{stem}{REGRESSION_SUFFIX}{extension}"


def config_file(path: str, report: bool = True) -> str:
    """Return the configuration file to read for ``path``.

    In regression mode this is the regression variant when it exists, else ``path``.
    The choice is printed once per file when ``report`` is True.
    """
    chosen = path
    if regression_mode():
        variant = regression_variant(path)
        if os.path.exists(variant):
            chosen = variant
    if report and chosen not in _reported:
        _reported.add(chosen)
        mode = f"{TEST_MODE_VARIABLE}=1" if regression_mode() else "normal mode"
        print(f"[hcdworkflow] Configuration file ({mode}): {chosen}", flush=True)
    return chosen
