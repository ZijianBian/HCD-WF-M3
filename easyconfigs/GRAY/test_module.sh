#!/bin/bash
# Post-install test of a GRAY module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# The repository has no ci-sdcc run script: runs the documented sequence (run_gray.py = iWrap actor,
# run_muscle = MUSCLE3 actor) on inputs/scenario[_dd3].yaml (public ITER 134173/106, t = 200 s, EC
# launchers from inputs/ec_waveforms[_dd3].yaml through Waveform-Cooker) from a run directory made by
# gray_run_setup, with the outputs in <workdir>/out (run_out 1: iWrap, run_out 2: MUSCLE3) and the
# iWrap sandbox in <workdir>/sandbox. Appends the results to <summary_file>; returns 0 when both runs
# succeed and wrote waves.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}

say() { echo "$*" | tee -a "$summary"; }

mkdir -p "$work"
run=$work/run
gray_run_setup "$run" > "$work/setup.log" 2>&1 || { say "setup: FAILED (see $work/setup.log)"; exit 1; }
say "run directory: $run"
cd "$run" || exit 1

case "${IMAS_VERSION:-}" in
    3.*) scen=inputs/scenario_dd3.yaml; ddv=3 ;;
    *)   scen=inputs/scenario.yaml; ddv=4 ;;
esac
sed -i -e "s|^output_user_or_path:.*|output_user_or_path: $work/out|" "$scen"
export GRAY_SANDBOX_DIR=$work/sandbox
export MPLCONFIGDIR=$work/matplotlib XDG_CACHE_HOME=$work/cache

status=0
for mode in iwrap muscle3; do
    if [[ $mode == iwrap ]]; then
        sed -i -e 's|^run_out:.*|run_out:             1|' "$scen"
        cmd=(python run_gray.py)
    else
        sed -i -e 's|^run_out:.*|run_out:             2|' "$scen"
        cmd=(./run_muscle)
    fi
    log=$work/$mode.log
    t0=$(date +%s)
    "${cmd[@]}" > "$log" 2>&1
    rc=$?
    t1=$(date +%s)
    say "$mode: rc=$rc, $((t1 - t0)) s (log $log)"
    [[ $rc -eq 0 ]] || status=1
done
pulse=$(sed -n 's/^pulse:[[:space:]]*\([0-9]*\).*/\1/p' "$scen")
db=$(sed -n 's/^output_database:[[:space:]]*\([A-Za-z0-9_]*\).*/\1/p' "$scen")

# waves of the two runs: number of beams and total absorbed power
python - "$work/out/$db/$ddv/$pulse/1" "$work/out/$db/$ddv/$pulse/2" >> "$summary" 2>&1 <<'EOF'
import sys
import imas
res = {}
for label, path in zip(("iwrap", "muscle3"), sys.argv[1:]):
    try:
        with imas.DBEntry(f"imas:hdf5?path={path}", "r") as db:
            waves = db.get("waves", autoconvert=False)
        tot = sum(float(cw.global_quantities[0].power) for cw in waves.coherent_wave)
        res[label] = tot
        print(f"  {label}: {path}: {len(waves.coherent_wave)} beams, {len(waves.time)} times, "
              f"absorbed power (first time) = {tot:.6e} W")
    except Exception as exc:
        print(f"  {label}: cannot read waves from {path}: {exc}")
if len(res) == 2:
    a, b = res["iwrap"], res["muscle3"]
    print(f"  iwrap vs muscle3: relative difference {abs(a - b) / max(abs(a), abs(b), 1e-30):.3e}")
    sys.exit(0 if a > 0 else 1)
sys.exit(1)
EOF
[[ $? -eq 0 ]] || status=1
say "test status: $([[ $status -eq 0 ]] && echo PASSED || echo FAILED)"
exit $status
