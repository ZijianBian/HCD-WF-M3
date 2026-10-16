#!/bin/bash
# Source from the repository root. Module versions are supplied by the caller.
if [[ -z "${MODULES:-}" ]]; then
    echo "ERROR: Set MODULES to a space-separated list of module names." >&2
    return 1
fi

read -r -a RUNMODULES <<< "$MODULES"
if [[ ${#RUNMODULES[@]} -eq 0 ]]; then
    echo "ERROR: The module list is empty." >&2
    return 1
fi

source /etc/profile.d/modules.sh || return 1
module use /work/imas/etc/modules/all || return 1
shopt -s expand_aliases
module purge || return 1
for module_name in "${RUNMODULES[@]}"; do
    module load "$module_name" || return 1
done

# Determine IMAS version from the Fortran module if not already set.
if [[ -z "${IMAS_VERSION:-}" ]] && pkg-config --exists al-fortran 2>/dev/null; then
    IMAS_VERSION=$(pkg-config --modversion al-fortran | cut -d- -f1)
    export IMAS_VERSION
fi

echo "> Loaded modules"
module list 2>&1
echo "> Using IMAS_VERSION=${IMAS_VERSION:-unset}"
