#!/bin/bash
# hcd2core_sources_run_setup <run_dir>
#
# Creates a writable hcd2core-sources run directory from the run kit of the loaded HCD2CORE_SOURCES module
# ($EBROOTHCD2CORE_SOURCES/run_kit, the repository tree of the pinned commit with the build products and the
# build stamp of the module's combination). The files are copied; the iWrap actor package of the
# module ($EBROOTHCD2CORE_SOURCES/<actor>) is linked where the run scripts expect it, and it is also on
# PYTHONPATH.
#
# Then, from <run_dir>:
#     python run_hcd2core_sources.py   # iWrap actor (input/scenario.yaml: set output_user_or_path)
#     ./run_muscle                     # MUSCLE3 actor (run_hcd2core_sources.py + src/hcd2core_sources_m3.exe)
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge the
# modules (including HCD2CORE_SOURCES) and expect a local build; they are not copied.

set -euo pipefail

usage() {
    sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed -e '/^$/d' -e 's/^# \{0,1\}//'
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTHCD2CORE_SOURCES:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "hcd2core_sources_run_setup: load a HCD2CORE_SOURCES module with a run kit first (EBROOTHCD2CORE_SOURCES/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "hcd2core_sources_run_setup: $dest exists and is not empty" >&2
    exit 1
fi
mkdir -p "$dest"
dest=$(cd "$dest" && pwd -P)
kit=$root/run_kit

( cd "$kit" && tar --exclude='./config_sdcc*.sh' --exclude='./.module_actor_links' \
      --exclude='__pycache__' -cf - . ) | ( cd "$dest" && tar -xf - )
chmod -R u+w "$dest"

# <path in the run directory> <actor package of the module>
while read -r path actor; do
    [[ -n "$path" ]] || continue
    mkdir -p "$(dirname "$dest/$path")"
    ln -sfn "$root/$actor" "$dest/$path"
done < "$kit/.module_actor_links"

echo "hcd2core-sources run directory: $dest (module $root, COMBO ${COMBO:-?}, DD ${IMAS_VERSION:-?})"
echo "  cd $dest"
sed -n 's/^#     /  /p' "${BASH_SOURCE[0]}"
