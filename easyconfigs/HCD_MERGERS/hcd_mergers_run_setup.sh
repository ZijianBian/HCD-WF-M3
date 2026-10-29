#!/bin/bash
# hcd_mergers_run_setup <run_dir>
#
# Creates a writable HCD_MERGERS run directory from the run kit of the loaded HCD_MERGERS module
# ($EBROOTHCD_MERGERS/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (merge_*/ with the MUSCLE3 actors, build stamp .build_combo) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>:
#     python run_mergers.py    # iWrap actors (4 mergers on dummy IDSs)
#     ./run_muscle             # MUSCLE3 actors (muscle_manager --start-all coupling.ymmsl)
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including HCD_MERGERS) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTHCD_MERGERS:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "hcd_mergers_run_setup: load a HCD_MERGERS module with a run kit first (EBROOTHCD_MERGERS/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "hcd_mergers_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest
echo "HCD_MERGERS run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  python run_mergers.py    # iWrap actors (4 mergers on dummy IDSs)"
echo "  ./run_muscle             # MUSCLE3 actors (muscle_manager --start-all coupling.ymmsl)"
