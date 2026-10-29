#!/usr/bin/env python3
"""Writes the three GRAY easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), gray_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/g/GRAY/gray-<VERSION>.tar.gz (git archive of COMMIT from the local gray clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

TEST = r'''#!/bin/bash
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
'''

CODE = dict(
    name='GRAY', code='gray', actor='gray', title='EC beam tracing',
    repo=hcd.repo('nolicense/gray', 'GRAY'), repo_name='gray',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/gray',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='9792659ddb9d67561d0b6d9a16acaf5d022022af', describe='1.0.0-7-g9792659',
    description='GRAY quasi-optical beam-tracing code for electron cyclotron heating and current drive.',
    contents=('Fortran library (lib/libgray.a, include/gray), MUSCLE3 actor executable (bin/gray_m3.exe, also '
              'gray/gray_m3.exe), iWrap actor package gray (on PYTHONPATH), and the run kit run_kit (run_gray.py, '
              'run_muscle, coupling.ymmsl, inputs/). Built with DEBUG=1 as ci-sdcc/st01 + st02 and build.sh.'),
    yaml_prefix='gray',
    build_source='ci-sdcc/st01-build-code.sh (DEBUG=1, as st02 and build.sh)',
    build_cmds=['make clean xmlval libgray.a DEBUG=1 FC="$FC"', 'make m3 DEBUG=1 FC="$FC"'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make iwrapactor DEBUG=1 FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='gray_m3.exe',
    files_to_copy=[(['gray_m3.exe'], 'bin'), (['libgray.a'], 'lib'), (['*.mod'], 'include/gray')],
    kit_products=[('gray_m3.exe', 'gray_m3.exe')],
    kit_required=['run_gray.py', 'run_muscle', 'coupling.ymmsl', 'inputs/scenario.yaml', 'inputs/scenario_dd3.yaml',
                  'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libgray.a', 'run_kit/run_gray.py', 'run_kit/inputs/scenario.yaml',
                  'run_kit/inputs/scenario_dd3.yaml'],
    sanity_dirs=['run_kit/inputs'],
    run_lines=['python run_gray.py      # iWrap actor (inputs/scenario[_dd3].yaml: output_user_or_path, run_out)',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    # deps.yaml names the user-tree build 14.4.0.dev1: replaced by the official 1.10.0 (same mirror-steering
    # API, ec_mirror_add_dynamic)
    cooker_map={'Waveform-Cooker/14.4.0.dev1': 'Waveform-Cooker/1.10.0-GCCcore-{gcc}'},
    cooker_note='official 1.10.0 for DD4 where deps.yaml names the user build 14.4.0.dev1: mirror steering '
                'ec_mirror_add_dynamic; 1.9.0 as in deps.yaml for DD3',
    cooker_api={'intel-2025b-dd4': 'add_dynamic, ec_mirror_add_dynamic',
                'intel-2025b-dd3': 'add_dynamic, ec_add_dynamic, ec_adjust',
                'intel-2023b-dd3': 'add_dynamic, ec_add_dynamic, ec_adjust'},
    test_script=TEST,
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
