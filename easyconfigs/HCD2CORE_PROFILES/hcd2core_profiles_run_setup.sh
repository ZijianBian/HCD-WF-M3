#!/bin/bash
# hcd2core_profiles_run_setup <run_dir>
#
# Creates a writable HCD2CORE_PROFILES run directory from the run kit of the loaded HCD2CORE_PROFILES module
# ($EBROOTHCD2CORE_PROFILES/run_kit): the run scripts, inputs and yMMSL files are copied, the links to the build
# products of the module (hcd2core_profiles/ with the MUSCLE3 actor, build stamp .build_combo) are kept as links. The iWrap actor packages are taken from
# the module through PYTHONPATH.
#
# Then, from <run_dir>:
#     ./run_hcd2core_profilescode --src <uri> --dest <uri> --time <s>   # iWrap actor (CI case)
#     ./run_muscle   # MUSCLE3 actor; edit --src/--dest/--time in coupling.ymmsl first
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge
# the modules (including HCD2CORE_PROFILES) and expect a local build; they are not part of the run kit.

set -euo pipefail

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTHCD2CORE_PROFILES:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "hcd2core_profiles_run_setup: load a HCD2CORE_PROFILES module with a run kit first (EBROOTHCD2CORE_PROFILES/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "hcd2core_profiles_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

run=$dest
echo "HCD2CORE_PROFILES run directory: $run (module $root, DD ${IMAS_VERSION:-?})"
echo "  cd $run"
echo "  ./run_hcd2core_profilescode --src <uri> --dest <uri> --time <s>   # iWrap actor (CI case)"
echo "  ./run_muscle   # MUSCLE3 actor; edit --src/--dest/--time in coupling.ymmsl first"
