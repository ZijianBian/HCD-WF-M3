#!/bin/bash
# risk_run_setup <run_dir>
#
# Creates a writable RISK run directory from the run kit of the loaded RISK module
# ($EBROOTRISK/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (risk_m3.exe, risk/ actor package, build stamp .build_combo) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>:
#     ./run_risk -c input   # iWrap actor (MPI processes: nproc of input/scenario.yaml)
#     ./run_muscle          # MUSCLE3 actor (risk_m3.exe on resources.risk.mpi_processes)
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including RISK) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTRISK:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "risk_run_setup: load a RISK module with a run kit first (EBROOTRISK/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "risk_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest
echo "RISK run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  ./run_risk -c input   # iWrap actor (MPI processes: nproc of input/scenario.yaml)"
echo "  ./run_muscle          # MUSCLE3 actor (risk_m3.exe on resources.risk.mpi_processes)"
