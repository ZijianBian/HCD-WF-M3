#!/bin/bash
# chease_run_setup <run_dir>
#
# Creates a writable CHEASE run directory from the run kit of the loaded CHEASE module
# ($EBROOTCHEASE/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (chease/ = MUSCLE3 actor package, build stamp python/.build_combo) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>/python:
#     python run_chease.py --scenario <scenario.yaml>          # iWrap actor (default ../input/scenario.yaml)
#     CHEASE_SCENARIO=<scenario.yaml> ./run_muscle3          # MUSCLE3 actor
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including CHEASE) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTCHEASE:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "chease_run_setup: load a CHEASE module with a run kit first (EBROOTCHEASE/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "chease_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest/python
echo "CHEASE run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  python run_chease.py --scenario <scenario.yaml>          # iWrap actor (default ../input/scenario.yaml)"
echo "  CHEASE_SCENARIO=<scenario.yaml> ./run_muscle3          # MUSCLE3 actor"
