"""Stack size limit of the H&CD workflow process.

The Fortran actors run inside the workflow process (iWrap actors) or as its child processes (MPI actors) and
need a large stack: with the usual 8 MB default soft limit some of them stop with a segmentation fault.
"""

import os
import resource
import sys

_RESTARTED = "HCDWF_STACK_LIMIT_RAISED"


def raise_stack_limit():
    """Raise the soft stack limit to the hard limit and restart the launcher with it.

    The soft limit becomes unlimited when the hard limit is unlimited, otherwise it becomes the hard limit.
    The launcher is restarted once (exec of the same command line) so that the Python interpreter, its
    threads and the in-process actors start with the raised limit; child processes inherit it.
    """
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    if soft == hard or os.environ.get(_RESTARTED) == "1":
        return
    resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    os.environ[_RESTARTED] = "1"
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(sys.executable, [sys.executable, *sys.argv])
