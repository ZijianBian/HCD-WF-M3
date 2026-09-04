#!/usr/bin/env bash
set -euo pipefail

# Rabbit is built with GCC while the other Pure-M3 actors use Intel.  Keep the
# runtimes isolated in separate processes, but use the same DD and MUSCLE wire
# protocol as the existing HCD stack.
if ! type module >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source /etc/profile.d/modules.sh
fi

module purge
module load IMAS-Fortran/5.5.0-foss-2023b-DD-4.1.0
module load XMLlib/3.3.2-GCC-13.2.0
module load INTERPOS/9.2.0-gfbf-2023b
module load MUSCLE3/0.8.0-foss-2023b

actor_folder="${ACTOR_FOLDER:-${HOME}/public/PYTHON_ACTORS}"
exec "${actor_folder}/rabbit/rabbit_m3.exe" "$@"
