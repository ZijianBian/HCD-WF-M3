#!/usr/bin/env bash
# Run a saved workflow configuration without requiring the graphical interface.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./run.sh {legacy|hybrid|pure} CONFIG_DIRECTORY [TOPOLOGY.ymmsl]

CONFIG_DIRECTORY must contain input_workflow.xml and the selected actors'
parameter files, as saved by hcd_gui. Source config_hcd_iter_sdcc.sh first.

Hybrid defaults to topologies/hybrid.ymmsl; Pure defaults to
topologies/pure.ymmsl and includes the actors selected in input_workflow.xml.
Generated MUSCLE3 configuration and output go into CONFIG_DIRECTORY/.hcd_gui_runs/.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 2 || $# -gt 3 ]]; then
    usage >&2
    exit 2
fi
case "$1" in
    legacy|hybrid|pure) ;;
    *) echo "ERROR: Unknown execution mode: $1" >&2; exit 2 ;;
esac
if [[ "$1" == legacy && $# -eq 3 ]]; then
    echo "ERROR: Legacy mode does not use a topology file." >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "$SCRIPT_DIR" "$@" <<'PY'
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from gui.launch_config import (
    LaunchConfigurationError,
    default_ymmsl_path,
    muscle_manager_command,
    prepare_muscle_launch,
)

mode = sys.argv[2]
configuration = Path(sys.argv[3]).expanduser().resolve()
try:
    input_file = configuration / "input_workflow.xml"
    if not input_file.is_file():
        raise LaunchConfigurationError(
            "No input_workflow.xml found in configuration folder {}.".format(configuration)
        )
    ET.parse(str(input_file))
    environment = os.environ.copy()
    environment.pop("MUSCLE_CONFIGURATION", None)
    environment.pop("MUSCLE_INSTANCE", None)
    environment.setdefault("ACTOR_FOLDER", str(root / "PYTHON_ACTORS"))
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(root), environment.get("PYTHONPATH", "")))
    )
    if mode == "legacy":
        command = [sys.executable, str(root / "workflow/workflow_driver.py"),
                   str(configuration), "0"]
    else:
        topology = (sys.argv[4] if len(sys.argv) == 5 else
                    environment.get("HCD_{}_YMMSL".format(mode.upper())) or
                    default_ymmsl_path(mode, root))
        manager = shutil.which("muscle_manager")
        if manager is None:
            raise LaunchConfigurationError(
                "Cannot find muscle_manager. Source config_hcd_iter_sdcc.sh first."
            )
        plan = prepare_muscle_launch(mode, configuration, topology, root)
        print("MUSCLE3 output: {}".format(plan.run_directory), flush=True)
        command = muscle_manager_command(plan, manager)
    os.chdir(str(root))
    os.execvpe(command[0], command, environment)
except (LaunchConfigurationError, OSError, ET.ParseError) as exc:
    print("ERROR: {}".format(exc), file=sys.stderr)
    sys.exit(2)
PY
