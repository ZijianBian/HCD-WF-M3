#!/bin/bash
# fpsim_run_setup <run_dir>
#
# Creates a writable FPSIM run directory from the run kit of the loaded FPSIM module
# ($EBROOTFPSIM/run_kit: the files of the repository at the module's commit with the build products
# tools/iccoup/iccoup_m3.exe and the build stamp .build_combo of the module's combination). The iWrap actor package
# iccoup is taken from the module through PYTHONPATH; actor.tar.gz (a copy of it, read by the ci-sdcc
# run scripts) is written into <run_dir>. ci-sdcc/resolve_deps.sh of the run kit takes the environment
# of the loaded module (no module purge), so the ci-sdcc scripts run with the module loaded.
#
# Run from <run_dir>:
#     bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=200 s, ITER_MD 110000/2, checks (ST03_DIR, default ./ci-st03)
#     python run_iccoup.py    # iWrap actor (ICCOUP_INPUT_URI, ICCOUP_MD_URI, ICCOUP_TIME, ICCOUP_OUTPUT_URI)
#     ./run_muscle            # MUSCLE3 actor (coupling.ymmsl)
# Do not source the config_sdcc*.sh env files of the repository: they purge the modules (including
# FPSIM) and select a local build; they are not copied.

set -euo pipefail

usage() {
    sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

if [[ -z "${EBROOTFPSIM:-}" || ! -d "$EBROOTFPSIM/run_kit" ]]; then
    echo "fpsim_run_setup: load a FPSIM module with a run kit first (EBROOTFPSIM/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "fpsim_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$EBROOTFPSIM/run_kit

( cd "$kit" && tar --exclude='./config_sdcc*.sh' --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"
tar --exclude='__pycache__' -czf "$dest/actor.tar.gz" -C "$EBROOTFPSIM" iccoup

echo "FPSIM run directory: $dest (module $EBROOTFPSIM, COMBO ${COMBO:-?}, DD ${IMAS_VERSION:-?})"
echo "  cd $dest"
echo "  bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=200 s, ITER_MD 110000/2, checks (ST03_DIR, default ./ci-st03)"
echo "  python run_iccoup.py    # iWrap actor (ICCOUP_INPUT_URI, ICCOUP_MD_URI, ICCOUP_TIME, ICCOUP_OUTPUT_URI)"
echo "  ./run_muscle            # MUSCLE3 actor (coupling.ymmsl)"
