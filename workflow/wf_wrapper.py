"""Compatibility shim for the renamed workflow driver.

The implementation lives in :mod:`workflow.workflow_driver`. Keep this module
temporarily so older ymmsl files and scripts that still execute
``workflow/wf_wrapper.py`` continue to work during the rename.
"""

from workflow.workflow_driver import *  # noqa: F401,F403
from workflow.workflow_driver import workflow_driver


wf_wrapper = workflow_driver


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python wf_wrapper.py <config_path> [m3_flag]")
        print("  config_path: Path to configuration folder")
        print("  m3_flag: 0=traditional iwrap, 1=MUSCLE3 macro (default: 0)")
        sys.exit(1)

    config_path = sys.argv[1]
    m3_flag = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    workflow_driver(config_path, m3_flag=m3_flag)
