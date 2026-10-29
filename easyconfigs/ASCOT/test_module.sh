#!/bin/bash
# Post-install test of an ASCOT module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with ascot_run_setup and runs the CI case ci-sdcc/st03-run-actor.sh of the
# run kit (without its st00-header line, see ../_lib/test_lib.sh) with the actor packages of the module
# (ACTOR_FOLDER=$EBROOTASCOT): ITER 130012/4 at t = 100 s, NBI ITER_MD 130000/2301, wall ITER_MD
# 116000/2; run 1 iWrap serial (bbnbi_serial -> ascot_serial, afsi), run 2 iWrap parallel on 2 MPI
# processes, run 3 MUSCLE3 (bbnbi_m3.exe -> ascot_m3.exe on 2 MPI processes each, afsi_m3.exe).
# Intel MPI starts its processes on this node (I_MPI_HYDRA_BOOTSTRAP=fork), at most 4 at a time.
# Outputs in <workdir>/st03. Returns the status of st03.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"

mkdir -p "$work"
run=$work/run
ascot_run_setup "$run" > "$work/setup.log" 2>&1 || { hcd_say "setup: FAILED (see $work/setup.log)"; exit 1; }
hcd_say "run directory: $run"
cd "$run" || exit 1
hcd_ci_copy ci-sdcc/st03-run-actor.sh "$work/st03_module.sh" || { hcd_say "st03 copy: FAILED"; exit 1; }

export FC=$(hcd_fc)
export ACTOR_FOLDER=$EBROOTASCOT
hcd_mpi_local
t0=$(date +%s)
ST03_DIR=$work/st03 bash "$work/st03_module.sh" > "$work/st03.log" 2>&1
rc=$?
hcd_say "st03 (iWrap serial, iWrap parallel, MUSCLE3): rc=$rc, $(( $(date +%s) - t0 )) s (log $work/st03.log)"
grep -E '^> Run [123]|^OK$|FAILED|ERROR' "$work/st03.log" | cut -c1-200 | tee -a "$summary"
for r in serial parallel m3; do
    [[ -f "$work/st03/$r/summary.json" ]] && hcd_say "summary $r: $work/st03/$r/summary.json"
done
exit $rc
