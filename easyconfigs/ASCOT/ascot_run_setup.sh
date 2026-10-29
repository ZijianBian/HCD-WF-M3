#!/bin/bash
# ascot_run_setup <run_dir>
#
# Creates a writable ASCOT run directory from the run kit of the loaded ASCOT module
# ($EBROOTASCOT/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (afsi_m3.exe, bbnbi_m3.exe, ascot_m3.exe, build stamp .build_combo) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>:
#     python run_ascot.py -c input   # iWrap actors (edit input/scenario.yaml first)
#     ./run_muscle                   # MUSCLE3 actors bbnbi -> ascot (2 MPI processes each), afsi
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including ASCOT) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTASCOT:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "ascot_run_setup: load a ASCOT module with a run kit first (EBROOTASCOT/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "ascot_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest
echo "ASCOT run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  python run_ascot.py -c input   # iWrap actors (edit input/scenario.yaml first)"
echo "  ./run_muscle                   # MUSCLE3 actors bbnbi -> ascot (2 MPI processes each), afsi"
