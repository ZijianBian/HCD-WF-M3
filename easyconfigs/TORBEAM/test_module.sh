#!/bin/bash
# Post-install test of a TORBEAM module, called by build_modules.sbatch with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with torbeam_run_setup, writes the outputs below <workdir>/out (run_out 1:
# iWrap actor, run_out 2: MUSCLE3 actor) and appends the results to <summary_file>.
# Returns 0 when both runs succeed and wrote their output entry.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}

say() { echo "$*" | tee -a "$summary"; }

mkdir -p "$work"
run_root=$work/run
torbeam_run_setup "$run_root" > "$work/setup.log" 2>&1 || { say "setup: FAILED (see $work/setup.log)"; exit 1; }
run=$(sed -n 's/^TORBEAM run directory: \([^ ]*\) .*/\1/p' "$work/setup.log")
say "run directory: $run"
cd "$run" || exit 1

scen=input/scenario.yaml
sed -i -e "s|^output_user_or_path:.*|output_user_or_path: $work/out|" "$scen"

status=0
for mode in iwrap muscle3; do
    if [[ $mode == iwrap ]]; then
        sed -i -e 's|^run_out:.*|run_out:             1|' "$scen"
        cmd=(./run_torbeam -c input)
    else
        sed -i -e 's|^run_out:.*|run_out:             2|' "$scen"
        cmd=(./run_muscle -c input)
    fi
    log=$work/$mode.log
    t0=$(date +%s)
    "${cmd[@]}" > "$log" 2>&1
    rc=$?
    t1=$(date +%s)
    # output entry printed by run_torbeam ("--> Output saved in folder <path>"), in the run log
    # (iWrap) or in the stdout of the MUSCLE3 instance that runs run_torbeam
    files=("$log")
    if [[ $mode == muscle3 ]]; then
        latest=$(ls -dt run_standalone_workflow_* 2>/dev/null | head -1)
        [[ -n "$latest" ]] && files+=("$latest"/instances/*/stdout.txt)
        say "muscle3 run dir: $run/${latest:-<none>}"
    fi
    entry=$(grep -h -- '--> Output saved in folder' "${files[@]}" 2>/dev/null | tail -1 | sed 's/.*folder //')
    say "$mode: rc=$rc, $((t1 - t0)) s, output entry ${entry:-<not printed>} (log $log)"
    [[ $rc -eq 0 && -n "$entry" && -d "$entry" ]] || status=1
    printf -v "entry_$mode" '%s' "$entry"
done

# Total absorbed power to electrons of the two runs (waves/coherent_wave/global_quantities/electrons/power_thermal)
python - "${entry_iwrap:-}" "${entry_muscle3:-}" >> "$summary" 2>&1 <<'EOF'
import sys
import imas
res = {}
for label, path in zip(("iwrap", "muscle3"), sys.argv[1:]):
    if not path:
        print(f"{label}: no output entry"); continue
    try:
        with imas.DBEntry(f"imas:hdf5?path={path}", "r") as db:
            waves = db.get("waves", autoconvert=False)
        tot = sum(float(gq.electrons.power_thermal) for cw in waves.coherent_wave for gq in cw.global_quantities[:1])
        res[label] = tot
        print(f"{label}: {len(waves.coherent_wave)} beams, electrons power_thermal (first time) = {tot:.6e} W")
    except Exception as exc:
        print(f"{label}: cannot read waves from {path}: {exc}")
if len(res) == 2:
    a, b = res["iwrap"], res["muscle3"]
    rel = abs(a - b) / max(abs(a), abs(b), 1e-30)
    print(f"iwrap vs muscle3: relative difference {rel:.3e}")
EOF
tail -3 "$summary"
exit $status
