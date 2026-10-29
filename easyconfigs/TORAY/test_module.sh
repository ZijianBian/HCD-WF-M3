#!/bin/bash
# Post-install test of a TORAY module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with toray_run_setup and runs the CI run case of the repository,
# ci-sdcc/st03-run-actor.sh (iWrap actor and MUSCLE3 actor, with its own result checks), with its work
# directory ST03_DIR=<workdir>/st03; outputs and MUSCLE3 run directories stay below <workdir>.
# Appends rc and the result lines to <summary_file>; returns 0 when the script succeeds and
# printed its PASSED line.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}

say() { echo "$*" | tee -a "$summary"; }

mkdir -p "$work"
run=$work/run
toray_run_setup "$run" > "$work/setup.log" 2>&1 || { say "setup: FAILED (see $work/setup.log)"; exit 1; }
say "run directory: $run"
cd "$run" || exit 1

export ST03_DIR=$work/st03
log=$work/st03.log
t0=$(date +%s)
bash ci-sdcc/st03-run-actor.sh > "$log" 2>&1
rc=$?
t1=$(date +%s)
say "ci-sdcc/st03-run-actor.sh: rc=$rc, $((t1 - t0)) s (log $log)"
grep -E "^($work|\./|/)[^ ]*: |PASSED|FAILED|iWrap vs|MUSCLE3 vs|agree" "$log" | grep -v '^+' | head -8 \
    | cut -c1-220 | sed 's/^/  /' | tee -a "$summary"
status=0
[[ $rc -eq 0 ]] && grep -q 'PASSED' "$log" || status=1
say "test status: $([[ $status -eq 0 ]] && echo PASSED || echo FAILED)"
exit $status
