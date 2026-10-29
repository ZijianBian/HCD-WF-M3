#!/bin/bash
# Functions shared by the test_module.sh scripts of the H&CD modules (sourced). A test_module.sh is
# called by tools/build_hcd_modules.sh in a clean environment with the new module loaded:
#     test_module.sh <workdir> <summary_file>
#
# Run-directory tests (set T_WORK=<workdir> and T_SUMMARY=<summary_file> before sourcing):
#   t_init <NAME> <helper>      run directory $RUN from the module's run kit (<helper> <workdir>/run),
#                               full module name $MODNAME, local MUSCLE3 instances (no srun), caches
#                               in the work directory, no __pycache__ written into the module
#   t_st03 <label> [VAR=value]  ci-sdcc/st03-run-actor.sh of the run kit with MODULES=$MODNAME (the
#                               script's resolve_deps.sh purges the modules and loads this module again)
#   t_cmd <label> <cmd...>      any command run from $RUN, log <workdir>/<label>.log
#   t_entry <label> <glob> <ids> <array>
#                               first IMAS HDF5 entry matching <glob>: <ids>.<array> must not be empty
#   t_done                      prints the summary tail and returns the overall status
#
# CI-script tests (set summary=<summary_file> before sourcing):
#   hcd_say <text>              print and append to $summary
#   hcd_fc                      compiler of the loaded toolchain (ifort if available, else ifx), as
#                               ci-sdcc/st00-header.sh derives FC
#   hcd_ci_copy <script> <copy> copy of a ci-sdcc run script without its
#                               "source ./ci-sdcc/st00-header.sh" line: that header loads the
#                               modules of deps.yaml after a module purge (ci-sdcc/resolve_deps.sh),
#                               which would unload the module under test; FC, COMBO and IMAS_VERSION
#                               come from the module and hcd_fc instead
#   hcd_mpi_local               Intel MPI and muscle_manager start their processes on this node
#                               (I_MPI_HYDRA_BOOTSTRAP=fork, no Slurm step)

set -uo pipefail

T_STATUS=0

t_say() { echo "$*" | tee -a "$T_SUMMARY"; }

t_init() {
    local name=$1 helper=$2 m IFS=:
    MODNAME=""
    for m in ${LOADEDMODULES:-}; do
        [[ $m == "$name"/* ]] && MODNAME=$m
    done
    IFS=$' \t\n'
    [[ -n "$MODNAME" ]] || { t_say "test: no $name module loaded"; exit 1; }
    mkdir -p "$T_WORK"
    "$helper" "$T_WORK/run" > "$T_WORK/setup.log" 2>&1 || { t_say "setup: FAILED (see $T_WORK/setup.log)"; exit 1; }
    RUN=$T_WORK/run
    t_say "module: $MODNAME, run directory: $RUN"
    # MUSCLE3 instances are started by muscle_manager on this node, not through srun
    unset SLURM_JOB_ID
    export PYTHONDONTWRITEBYTECODE=1
    export MPLCONFIGDIR=$T_WORK/cache/matplotlib XDG_CACHE_HOME=$T_WORK/cache MPLBACKEND=Agg
    export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
    mkdir -p "$MPLCONFIGDIR"
}

t_report() {   # <label> <rc> <seconds> <log>
    local label=$1 rc=$2 dt=$3 log=$4
    t_say "$label: rc=$rc, ${dt} s (log $log)"
    grep -E 'PASSED|FAILED|ERROR|agree|differ|relative difference|power|Total|total' "$log" 2>/dev/null \
        | grep -vE '^\s*(export|echo|\+)' | tail -6 | cut -c1-200 | sed 's/^/    /' | tee -a "$T_SUMMARY"
    [[ $rc -eq 0 ]] || T_STATUS=1
}

t_st03() {
    local label=$1; shift
    local log=$T_WORK/$label.log t0 rc
    t0=$(date +%s)
    ( cd "$RUN" && env MODULES="$MODNAME" "$@" bash ci-sdcc/st03-run-actor.sh ) > "$log" 2>&1
    rc=$?
    t_report "$label" "$rc" "$(( $(date +%s) - t0 ))" "$log"
}

t_cmd() {
    local label=$1; shift
    local log=$T_WORK/$label.log t0 rc
    t0=$(date +%s)
    ( cd "$RUN" && "$@" ) > "$log" 2>&1
    rc=$?
    t_report "$label" "$rc" "$(( $(date +%s) - t0 ))" "$log"
}

t_entry() {
    local label=$1 pattern=$2 ids=$3 array=$4 rc
    python - "$pattern" "$ids" "$array" >> "$T_SUMMARY" 2>&1 <<'EOF'
import glob, os, sys
import imas
pattern, ids, array = sys.argv[1:4]
entries = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(pattern, 'master.h5')))
if not entries:
    sys.exit('    no IMAS HDF5 entry matches %s' % pattern)
path = entries[0]
with imas.DBEntry('imas:hdf5?path=' + path, 'r') as db:
    obj = db.get(ids)
n = len(getattr(obj, array))
print('    %s: %s/%s has %d element(s) (%s)' % (path, ids, array, n, obj.ids_properties.version_put.data_dictionary))
sys.exit(0 if n > 0 else 1)
EOF
    rc=$?
    [[ $rc -eq 0 ]] || { t_say "$label: output check FAILED"; T_STATUS=1; }
}

t_done() {
    t_say "test status: $T_STATUS"
    return $T_STATUS
}

hcd_say() { echo "$*" | tee -a "$summary"; }

hcd_fc() {
    if command -v ifort >/dev/null 2>&1; then echo ifort; else echo ifx; fi
}

hcd_ci_copy() {
    local src=$1 dst=$2
    sed -e '/^source \.\/ci-sdcc\/st00-header\.sh/d' "$src" > "$dst" || return 1
    if grep -q 'st00-header' "$dst"; then
        echo "hcd_ci_copy: $src still sources st00-header.sh" >&2
        return 1
    fi
    if ! grep -q 'st00-header' "$src"; then
        echo "hcd_ci_copy: $src does not source st00-header.sh (format changed?)" >&2
        return 1
    fi
}

hcd_mpi_local() {
    unset SLURM_JOB_ID
    export I_MPI_HYDRA_BOOTSTRAP=fork
}
