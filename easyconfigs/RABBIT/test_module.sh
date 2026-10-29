#!/bin/bash
# Post-install test of a RABBIT module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with rabbit_run_setup and runs the CI case ci-sdcc/st03-run-actor.sh of the
# run kit (without its st00-header line, see ../_lib/test_lib.sh): public ITER 130012/4 and ITER_MD
# 116000/2, two time slices from t = 100 s, as iWrap actor (run_rabbit.py) and as MUSCLE3 actor
# (run_muscle), with the actor package of the module (ACTOR_FOLDER=$EBROOTRABBIT). Outputs, sandbox
# and logs in <workdir>/st03. Returns the status of st03 (non-zero if a run fails or its
# distributions IDS is empty or without power).

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"

mkdir -p "$work"
run=$work/run
rabbit_run_setup "$run" > "$work/setup.log" 2>&1 || { hcd_say "setup: FAILED (see $work/setup.log)"; exit 1; }
hcd_say "run directory: $run"
cd "$run" || exit 1
hcd_ci_copy ci-sdcc/st03-run-actor.sh "$work/st03_module.sh" || { hcd_say "st03 copy: FAILED"; exit 1; }

export FC=$(hcd_fc)
export ACTOR_FOLDER=$EBROOTRABBIT
hcd_mpi_local
t0=$(date +%s)
ST03_DIR=$work/st03 RUN_M3=1 bash "$work/st03_module.sh" > "$work/st03.log" 2>&1
rc=$?
hcd_say "st03 (iWrap + MUSCLE3): rc=$rc, $(( $(date +%s) - t0 )) s (log $work/st03.log)"
grep -E 'time slices, .* beams|MUSCLE3 vs iWrap|FAILED' "$work/st03.log" | cut -c1-240 | tee -a "$summary"
exit $rc
