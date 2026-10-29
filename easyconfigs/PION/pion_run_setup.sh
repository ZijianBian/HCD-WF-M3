#!/bin/bash
# pion_run_setup <run_dir>
#
# Creates a writable pion run directory from the run kit of the loaded PION module
# ($EBROOTPION/run_kit, the repository tree of the pinned commit with the build products and the
# build stamp of the module's combination). The files are copied; the iWrap actor package of the
# module ($EBROOTPION/<actor>) is linked where the run scripts expect it, and it is also on
# PYTHONPATH.
#
# Then, from <run_dir>:
#     python run_pion.py -c input    # iWrap actor (input/scenario.yaml, PION_* variables)
#     ./run_muscle                   # MUSCLE3 actor (run_pion.py + pion_m3.exe)
#     MODULES=$(module -t list 2>&1 | grep ^PION/) bash ci-sdcc/st03-run-actor.sh   # CI case
# Do not source the config_sdcc*.sh env files of the repository in the run directory: they purge the
# modules (including PION) and expect a local build; they are not copied.

set -euo pipefail

usage() {
    sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed -e '/^$/d' -e 's/^# \{0,1\}//'
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac

root=${EBROOTPION:-}
if [[ -z "$root" || ! -d "$root/run_kit" ]]; then
    echo "pion_run_setup: load a PION module with a run kit first (EBROOTPION/run_kit)" >&2
    exit 1
fi

dest=$1
if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "pion_run_setup: $dest exists and is not empty" >&2
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

echo "pion run directory: $dest (module $root, COMBO ${COMBO:-?}, DD ${IMAS_VERSION:-?})"
echo "  cd $dest"
sed -n 's/^#     /  /p' "${BASH_SOURCE[0]}"
