#!/bin/bash
# cyrano_run_setup <run_dir>
#
# Creates a writable CYRANO run directory from the run kit of the loaded CYRANO module
# ($EBROOTCYRANO/run_kit: the files of the repository at the module's commit with the build products
# cyrano_m3.exe and the build stamp .build_combo of the module's combination). The iWrap actor package
# cyrano is taken from the module through PYTHONPATH; actor.tar.gz (a copy of it, read by the ci-sdcc
# run scripts) is written into <run_dir>. ci-sdcc/resolve_deps.sh of the run kit takes the environment
# of the loaded module (no module purge), so the ci-sdcc scripts run with the module loaded.
#
# Run from <run_dir>:
#     bash ci-sdcc/st05-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=200 s, ITER_MD 110000/2, checks (ST05_DIR, default ./ci-st05)
#     python run_cyrano.py    # iWrap actor (CYRANO_INPUT_URI, CYRANO_MD_URI, CYRANO_TIME, CYRANO_OUTPUT_URI)
#     ./run_muscle            # MUSCLE3 actor (coupling.ymmsl)
# Do not source the config_sdcc*.sh env files of the repository: they purge the modules (including
# CYRANO) and select a local build; they are not copied.

set -euo pipefail

usage() {
    sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

if [[ -z "${EBROOTCYRANO:-}" || ! -d "$EBROOTCYRANO/run_kit" ]]; then
    echo "cyrano_run_setup: load a CYRANO module with a run kit first (EBROOTCYRANO/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "cyrano_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$EBROOTCYRANO/run_kit

( cd "$kit" && tar --exclude='./config_sdcc*.sh' --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"
tar --exclude='__pycache__' -czf "$dest/actor.tar.gz" -C "$EBROOTCYRANO" cyrano

echo "CYRANO run directory: $dest (module $EBROOTCYRANO, COMBO ${COMBO:-?}, DD ${IMAS_VERSION:-?})"
echo "  cd $dest"
echo "  bash ci-sdcc/st05-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=200 s, ITER_MD 110000/2, checks (ST05_DIR, default ./ci-st05)"
echo "  python run_cyrano.py    # iWrap actor (CYRANO_INPUT_URI, CYRANO_MD_URI, CYRANO_TIME, CYRANO_OUTPUT_URI)"
echo "  ./run_muscle            # MUSCLE3 actor (coupling.ymmsl)"
