#!/bin/bash
# Post-install test of a RISK module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with risk_run_setup and runs, from it, with the module's actor package:
#  1. the CI case ci-sdcc/st03-run-actor.sh (without its st00-header line, see ../_lib/test_lib.sh):
#     public ITER 130012/5 at t = 200 s, iWrap actor on 2 MPI processes (nproc of st03-scenario.yaml),
#     outputs in <workdir>/st03;
#  2. the same case as MUSCLE3 actor (run_muscle, risk_m3.exe on the 4 MPI processes of
#     coupling.ymmsl), output <workdir>/m3/imasdb, checked with the check of st03;
#  3. the FRUIT regression tests ci-sdcc/st05-run-actor.sh (outputs in <workdir>/st05).
# Intel MPI starts its processes on this node (I_MPI_HYDRA_BOOTSTRAP=fork), at most 4.
# Returns 0 when the three steps succeed.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"
CODE=risk
DB=RISK

mkdir -p "$work"
run=$work/run
${CODE}_run_setup "$run" > "$work/setup.log" 2>&1 || { hcd_say "setup: FAILED (see $work/setup.log)"; exit 1; }
hcd_say "run directory: $run"
cd "$run" || exit 1
for st in st03 st05; do
    hcd_ci_copy ci-sdcc/$st-run-actor.sh "$work/${st}_module.sh" || { hcd_say "$st copy: FAILED"; exit 1; }
done
# the result check of st03 (python heredoc), reused for the MUSCLE3 run
awk '/<<.PYEOF.$/ {f = 1; next} /^PYEOF$/ {f = 0} f' ci-sdcc/st03-run-actor.sh > "$work/check_st03.py"

export FC=$(hcd_fc)
export MPLCONFIGDIR=$work/cache/matplotlib XDG_CACHE_HOME=$work/cache OMP_NUM_THREADS=1
hcd_mpi_local
DDV=${IMAS_VERSION%%.*}
status=0

# 1. iWrap actor, CI case
t0=$(date +%s)
ST03_DIR=$work/st03 bash "$work/st03_module.sh" > "$work/st03.log" 2>&1
rc=$?
hcd_say "st03 iwrap: rc=$rc, $(( $(date +%s) - t0 )) s (log $work/st03.log)"
grep -E 'distributions, total collisional power|CHECK PASSED|FAILED' "$work/st03.log" | cut -c1-200 | tee -a "$summary"
[[ $rc -eq 0 ]] || status=1

# 2. MUSCLE3 actor, same scenario and code parameters as st03 (input/ of the run directory)
sed "s#__ST03_IMASDB__#$work/m3/imasdb#" ci-sdcc/st03-scenario.yaml > input/scenario.yaml
export ${DB}_SANDBOX_DIR=$work/m3/sandbox
mkdir -p "$work/m3"
t0=$(date +%s)
./run_muscle > "$work/muscle3.log" 2>&1
rc=$?
latest=$(ls -dt run_${CODE}_standalone_workflow_* 2>/dev/null | head -1)
hcd_say "muscle3: rc=$rc, $(( $(date +%s) - t0 )) s (run dir $run/${latest:-<none>}, log $work/muscle3.log)"
python "$work/check_st03.py" "$work/m3/imasdb/$DB/$DDV/130012/1" > "$work/check_m3.log" 2>&1
crc=$?
cut -c1-200 "$work/check_m3.log" | grep -E 'total collisional power|CHECK PASSED|FAILED|Error' | tee -a "$summary"
[[ $rc -eq 0 && $crc -eq 0 ]] || status=1

# 3. FRUIT regression tests
t0=$(date +%s)
ST05_DIR=$work/st05 bash "$work/st05_module.sh" > "$work/st05.log" 2>&1
rc=$?
hcd_say "st05 FRUIT: rc=$rc, $(( $(date +%s) - t0 )) s (log $work/st05.log, FRUIT output $run/out.txt)"
grep -E 'Total asserts|Successful asserts|Failed asserts|FRUIT asserts run' out.txt "$work/st05.log" 2>/dev/null \
    | tail -4 | cut -c1-200 | tee -a "$summary"
[[ $rc -eq 0 ]] || status=1

exit $status
