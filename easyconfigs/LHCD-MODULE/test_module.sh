#!/bin/bash
# Post-install test of an LHCD-MODULE module, called by build_hcd_modules.sh with the module loaded in
# a clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with lhcd_module_run_setup and runs the CI case ci-sdcc/st03-run-actor.sh of
# the run kit (without its st00-header line, see ../_lib/test_lib.sh) with the actor package of the module
# (ACTOR_FOLDER=$EBROOTLHCDMINMODULE): WEST 57757 at t = 87.5 s from the CI entry of the kit, as iWrap
# actor (run_lhcd.py) and as MUSCLE3 actor (run_muscle); st03 checks the waves IDS and that both runs
# are identical. Outputs in <workdir>/st03. Returns the status of st03.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"

mkdir -p "$work"
run=$work/run
lhcd_module_run_setup "$run" > "$work/setup.log" 2>&1 || { hcd_say "setup: FAILED (see $work/setup.log)"; exit 1; }
hcd_say "run directory: $run"
cd "$run" || exit 1
hcd_ci_copy ci-sdcc/st03-run-actor.sh "$work/st03_module.sh" || { hcd_say "st03 copy: FAILED"; exit 1; }

export ACTOR_FOLDER=$EBROOTLHCDMINMODULE
unset SLURM_JOB_ID
t0=$(date +%s)
ST03_DIR=$work/st03 bash "$work/st03_module.sh" > "$work/st03.log" 2>&1
rc=$?
hcd_say "st03 (iWrap + MUSCLE3): rc=$rc, $(( $(date +%s) - t0 )) s (log $work/st03.log)"
grep -E ': power .* W, |runs are identical|FAILED|ERROR' "$work/st03.log" | cut -c1-220 | tee -a "$summary"
exit $rc
