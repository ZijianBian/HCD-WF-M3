"""Compatibility entry point for the shared in-process workflow driver."""

from workflow.workflow_driver import workflow_driver


wf_wrapper = workflow_driver


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python wf_wrapper.py <config_path>")
        print("  config_path: Path to configuration folder")
        sys.exit(1)

    workflow_driver(sys.argv[1])
