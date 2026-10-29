#!/bin/bash
# spot_run_setup <run_dir>
#
# Creates a writable SPOT run directory from the run kit of the loaded SPOT module
# ($EBROOTSPOT/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (spot_m3.exe, spot/ actor package, build stamp .build_combo) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>:
#     ./run_spot -c input   # iWrap actor (MPI processes: nproc of input/scenario.yaml)
#     ./run_muscle          # MUSCLE3 actor (spot_m3.exe on resources.spot.mpi_processes)
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including SPOT) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTSPOT:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "spot_run_setup: load a SPOT module with a run kit first (EBROOTSPOT/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "spot_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest
echo "SPOT run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  ./run_spot -c input   # iWrap actor (MPI processes: nproc of input/scenario.yaml)"
echo "  ./run_muscle          # MUSCLE3 actor (spot_m3.exe on resources.spot.mpi_processes)"
