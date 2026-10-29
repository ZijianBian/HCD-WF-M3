#!/bin/bash
# Post-install test of a CHEASE module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with chease_run_setup and runs, from its python/ folder, the scenario
# input/scenario.yaml of the repository (public ITER 134173/106, t = 200 s, one slice) with its output
# entries and iWrap sandbox in <workdir>: python/run_chease.py (iWrap Python actor, output run 8001)
# and python/run_muscle3 (MUSCLE3 actor chease_m3/bin/chease.exe, output run 8002). The repository has
# no ci-sdcc run script. Returns 0 when both runs succeed and wrote an equilibrium with finite psi.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"

mkdir -p "$work"
run=$work/run
chease_run_setup "$run" > "$work/setup.log" 2>&1 || { hcd_say "setup: FAILED (see $work/setup.log)"; exit 1; }
hcd_say "run directory: $run/python"
cd "$run/python" || exit 1
export MPLCONFIGDIR=$work/cache/matplotlib XDG_CACHE_HOME=$work/cache OMP_NUM_THREADS=1
unset SLURM_JOB_ID

for mode in iwrap muscle3; do
    run_out=8001
    [[ $mode == muscle3 ]] && run_out=8002
    sed -e "s#^output_user_or_path:.*#output_user_or_path: $work/out#" \
        -e "s#^output_tmp_folder:.*#output_tmp_folder:   $work/tmp_$mode#" \
        -e "s#^run_out:.*#run_out:             $run_out#" ../input/scenario.yaml > "$work/scenario_$mode.yaml"
done

status=0
t0=$(date +%s)
python run_chease.py --scenario "$work/scenario_iwrap.yaml" > "$work/iwrap.log" 2>&1
rc=$?
hcd_say "iwrap: rc=$rc, $(( $(date +%s) - t0 )) s (log $work/iwrap.log)"
[[ $rc -eq 0 ]] || status=1

t0=$(date +%s)
CHEASE_SCENARIO=$work/scenario_muscle3.yaml ./run_muscle3 > "$work/muscle3.log" 2>&1
rc=$?
latest=$(ls -dt run_chease_standalone_workflow_* 2>/dev/null | head -1)
hcd_say "muscle3: rc=$rc, $(( $(date +%s) - t0 )) s (run dir $run/python/${latest:-<none>}, log $work/muscle3.log)"
[[ $rc -eq 0 ]] || status=1

# output entries: "output_uri = ..." printed by run_chease.py (iWrap log, MUSCLE3 workflow instance)
python - "$work/iwrap.log" "${latest:+$latest/instances/workflow/stdout.txt}" >> "$summary" 2>&1 <<'EOF' || status=1
import re, sys
import numpy as np
import imas
ok = True
for label, log in zip(("iwrap", "muscle3"), sys.argv[1:]):
    uri = None
    try:
        for line in open(log):
            m = re.search(r"output_uri\s*=\s*(\S+)", line)
            if m:
                uri = m.group(1)
    except OSError:
        pass
    if not uri:
        print(f"{label}: no output_uri in {log}"); ok = False; continue
    try:
        with imas.DBEntry(uri, "r") as db:
            eq = db.get("equilibrium", autoconvert=False)
        ts = eq.time_slice[0]
        psi = np.asarray(ts.profiles_1d.psi)
        print(f"{label}: {uri}: {len(eq.time)} slice(s), t = {eq.time[0]} s, psi axis {psi[0]:.6e}, "
              f"boundary {psi[-1]:.6e} Wb, finite {bool(np.all(np.isfinite(psi)))}")
        ok = ok and psi.size > 0 and bool(np.all(np.isfinite(psi)))
    except Exception as exc:
        print(f"{label}: cannot read the equilibrium of {uri}: {exc}"); ok = False
sys.exit(0 if ok else 1)
EOF
tail -2 "$summary"
exit $status
