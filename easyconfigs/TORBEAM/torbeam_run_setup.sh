#!/bin/bash
# torbeam_run_setup <run_dir>
#
# Creates a writable TORBEAM run directory from the run kit of the loaded TORBEAM module
# ($EBROOTTORBEAM/test_imas, a copy of tests/test_imas of the repository): the scripts, input/
# and ymmsl/ are copied, build/ (library, torbeam_m3.exe, build stamp) is a symbolic link to the
# module. The iWrap actor package is taken from the module through PYTHONPATH.
#
# DD4 modules: run from <run_dir>; DD3 modules: run from <run_dir>/dd3.
#     ./run_torbeam -c input     # iWrap actor
#     ./run_muscle -c input      # MUSCLE3 actor (muscle_manager --start-all)
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge the
# modules (including TORBEAM) and use a local build; they are not copied.

set -euo pipefail

usage() {
    sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

if [[ -z "${EBROOTTORBEAM:-}" || ! -d "$EBROOTTORBEAM/test_imas" ]]; then
    echo "torbeam_run_setup: load a TORBEAM module with a run kit first (EBROOTTORBEAM/test_imas)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "torbeam_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$EBROOTTORBEAM/test_imas

( cd "$kit" && tar --exclude=./build --exclude='./config_sdcc*.sh' --exclude='./dd3/config_sdcc*.sh' \
      --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"
ln -s "$kit/build" "$dest/build"

case "${IMAS_VERSION:-}" in
    3.*) sub=dd3 ;;
    *)   sub=. ;;
esac
run=$dest
[[ "$sub" != . ]] && run=$dest/$sub

echo "TORBEAM run directory: $run (module $EBROOTTORBEAM, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  edit input/scenario.yaml (input entry, output_user_or_path, run_out) if needed"
echo "  ./run_torbeam -c input     # iWrap actor"
echo "  ./run_muscle -c input      # MUSCLE3 actor"
