#!/bin/bash
# lhcd_module_run_setup <run_dir>
#
# Creates a writable LHCD_METIS run directory from the run kit of the loaded LHCD-MODULE module
# ($EBROOTLHCDMINMODULE/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (lhcd_metis/ actor package with its build stamp) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>:
#     python run_lhcd.py -s <scenario.yaml> -c input/params.xml   # iWrap actor
#     ./run_muscle -s <scenario.yaml>                               # MUSCLE3 actor
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including LHCD-MODULE) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTLHCDMINMODULE:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "lhcd_module_run_setup: load a LHCD-MODULE module with a run kit first (EBROOTLHCDMINMODULE/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "lhcd_module_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest
echo "LHCD_METIS run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  python run_lhcd.py -s <scenario.yaml> -c input/params.xml   # iWrap actor"
echo "  ./run_muscle -s <scenario.yaml>                               # MUSCLE3 actor"
