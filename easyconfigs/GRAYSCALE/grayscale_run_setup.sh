#!/bin/bash
# grayscale_run_setup <run_dir>
#
# Creates a writable GRAYSCALE run directory from the run kit of the loaded GRAYSCALE module
# ($EBROOTGRAYSCALE/run_kit: the files of the repository at the module's commit with the build products
# grayscale_m3.exe and the build stamp .build_combo of the module's combination). The iWrap actor package
# grayscale is taken from the module through PYTHONPATH; actor.tar.gz (a copy of it, read by the ci-sdcc
# run scripts) is written into <run_dir>. ci-sdcc/resolve_deps.sh of the run kit takes the environment
# of the loaded module (no module purge), so the ci-sdcc scripts run with the module loaded.
#
# Run from <run_dir>:
#     bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/5, checks (ST03_DIR, default ./ci-st03)
#     python run_grayscale.py --src <uri> --dest <uri> --time <t>   # iWrap actor
#     ./run_muscle            # MUSCLE3 actor (coupling.ymmsl)
# Do not source the config_sdcc*.sh env files of the repository: they purge the modules (including
# GRAYSCALE) and select a local build; they are not copied.

set -euo pipefail

usage() {
    sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

if [[ -z "${EBROOTGRAYSCALE:-}" || ! -d "$EBROOTGRAYSCALE/run_kit" ]]; then
    echo "grayscale_run_setup: load a GRAYSCALE module with a run kit first (EBROOTGRAYSCALE/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "grayscale_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$EBROOTGRAYSCALE/run_kit

( cd "$kit" && tar --exclude='./config_sdcc*.sh' --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"
tar --exclude='__pycache__' -czf "$dest/actor.tar.gz" -C "$EBROOTGRAYSCALE" grayscale

echo "GRAYSCALE run directory: $dest (module $EBROOTGRAYSCALE, COMBO ${COMBO:-?}, DD ${IMAS_VERSION:-?})"
echo "  cd $dest"
echo "  bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/5, checks (ST03_DIR, default ./ci-st03)"
echo "  python run_grayscale.py --src <uri> --dest <uri> --time <t>   # iWrap actor"
echo "  ./run_muscle            # MUSCLE3 actor (coupling.ymmsl)"
