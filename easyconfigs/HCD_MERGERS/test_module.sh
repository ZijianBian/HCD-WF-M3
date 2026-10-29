#!/bin/bash
# Post-install test of an HCD_MERGERS module, called by build_hcd_modules.sh with the module loaded in
# a clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with hcd_mergers_run_setup and runs the CI case of ci-sdcc/st02-build-actor.sh
# (RUN_TEST): run_mergers.py with the iWrap actors, then run_muscle with the MUSCLE3 actors; each
# merger merges two dummy IDSs and the workflow prints "has 2 entries" once per merger.
# Returns 0 when both runs succeed and all four mergers returned 2 entries.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}

say() { echo "$*" | tee -a "$summary"; }

mkdir -p "$work"
run=$work/run
hcd_mergers_run_setup "$run" > "$work/setup.log" 2>&1 || { say "setup: FAILED (see $work/setup.log)"; exit 1; }
say "run directory: $run"
cd "$run" || exit 1
export MPLCONFIGDIR=$work/cache/matplotlib XDG_CACHE_HOME=$work/cache OMP_NUM_THREADS=1
# muscle_manager starts the instances on this node
unset SLURM_JOB_ID

status=0
count_entries() { grep -h -c ' has 2 entries' "$@" 2>/dev/null | awk '{s += $1} END {print s + 0}'; }

t0=$(date +%s)
python run_mergers.py > "$work/iwrap.log" 2>&1
rc=$?
n=$(count_entries "$work/iwrap.log")
say "iwrap: rc=$rc, $(( $(date +%s) - t0 )) s, $n of 4 mergers returned 2 entries (log $work/iwrap.log)"
[[ $rc -eq 0 && $n -eq 4 ]] || status=1

t0=$(date +%s)
./run_muscle > "$work/muscle3.log" 2>&1
rc=$?
latest=$(ls -dt run_hcd_mergers_standalone_workflow_* 2>/dev/null | head -1)
n=0
[[ -n "$latest" ]] && n=$(count_entries "$latest/instances/workflow/stdout.txt")
say "muscle3: rc=$rc, $(( $(date +%s) - t0 )) s, $n of 4 mergers returned 2 entries (run dir $run/${latest:-<none>}, log $work/muscle3.log)"
[[ $rc -eq 0 && $n -eq 4 ]] || status=1

exit $status
