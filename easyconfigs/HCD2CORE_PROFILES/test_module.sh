#!/bin/bash
# Post-install test of an HCD2CORE_PROFILES module, called by build_hcd_modules.sh with the module
# loaded in a clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with hcd2core_profiles_run_setup and runs the CI case of
# ci-sdcc/st02-build-actor.sh (RUN_TEST): run_hcd2core_profilescode on the public CI entry
# /work/imas/shared/heat/spot/fusreac/imasdb/ci/4/130012/3 at t = 298.48 s (iWrap actor, output
# <workdir>/out_iwrap), then run_muscle on the same case (MUSCLE3 actor, output <workdir>/out_m3).
# Returns 0 when both runs succeed and wrote core_profiles with fast-particle densities.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}

say() { echo "$*" | tee -a "$summary"; }

SRC='imas:hdf5?path=/work/imas/shared/heat/spot/fusreac/imasdb/ci/4/130012/3'
TIME=298.48

mkdir -p "$work"
run=$work/run
hcd2core_profiles_run_setup "$run" > "$work/setup.log" 2>&1 || { say "setup: FAILED (see $work/setup.log)"; exit 1; }
say "run directory: $run"
cd "$run" || exit 1
export MPLCONFIGDIR=$work/cache/matplotlib XDG_CACHE_HOME=$work/cache OMP_NUM_THREADS=1
# muscle_manager starts the instances on this node
unset SLURM_JOB_ID

status=0
t0=$(date +%s)
python run_hcd2core_profilescode --src "$SRC" --dest "imas:hdf5?path=$work/out_iwrap" --time $TIME \
    > "$work/iwrap.log" 2>&1
rc=$?
say "iwrap: rc=$rc, $(( $(date +%s) - t0 )) s, output $work/out_iwrap (log $work/iwrap.log)"
[[ $rc -eq 0 ]] || status=1

# MUSCLE3 run: output entry of the coupling file in the test directory
sed -i -e "s#imas:hdf5?path=/scratch/users/\$USER/hcd2core-profiles/out_m3#imas:hdf5?path=$work/out_m3#" coupling.ymmsl
mkdir -p "$work/out_m3"
t0=$(date +%s)
./run_muscle > "$work/muscle3.log" 2>&1
rc=$?
latest=$(ls -dt run_hcd2core_profiles_standalone_workflow_* 2>/dev/null | head -1)
say "muscle3: rc=$rc, $(( $(date +%s) - t0 )) s, output $work/out_m3 (run dir $run/${latest:-<none>}, log $work/muscle3.log)"
[[ $rc -eq 0 ]] || status=1

python - "$work/out_iwrap" "$work/out_m3" >> "$summary" 2>&1 <<'EOF' || status=1
import sys
import numpy as np
import imas
res = {}
for label, path in zip(("iwrap", "muscle3"), sys.argv[1:]):
    try:
        with imas.DBEntry(f"imas:hdf5?path={path}", "r") as db:
            cp = db.get("core_profiles", autoconvert=False)
        p1 = cp.profiles_1d[0]
        nfast = np.asarray(p1.electrons.density_fast)
        res[label] = nfast
        print(f"{label}: {len(cp.time)} time slice(s), electrons density_fast max {nfast.max():.6e} m-3, "
              f"{len(p1.ion)} ions")
    except Exception as exc:
        print(f"{label}: cannot read core_profiles from {path}: {exc}")
if len(res) != 2:
    sys.exit(1)
a, b = res["iwrap"], res["muscle3"]
print("iwrap vs muscle3: max relative difference of density_fast %.3e"
      % (np.max(np.abs(a - b)) / max(np.max(np.abs(a)), 1e-30)))
EOF
tail -3 "$summary"
exit $status
