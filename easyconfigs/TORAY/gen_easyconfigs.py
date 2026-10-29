#!/usr/bin/env python3
"""Writes the three TORAY easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), toray_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/t/TORAY/toray-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
COMMIT must be a pushed commit of origin/feature/DD3_and_DD4: when the branch moves, update COMMIT and
DESCRIBE, delete the old source archive and rerun (the Waveform-Cooker module follows deps.yaml of COMMIT).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='TORAY', code='toray', actor='toray', title='EC ray tracing',
    repo=hcd.repo('toray', 'TORAY'), repo_name='toray',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/toray',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='13c359b20b49cc6e5a02a69a33bc3061095a1720', describe='1.0.0-17-g13c359b',
    description='TORAY ray-tracing code for electron cyclotron heating and current drive.',
    contents=('Fortran library (lib/libtoray.a with lib/libnag.a, lib/libnet.a, include/toray), MUSCLE3 actor '
              'executable (bin/toray_m3.exe, also toray/toray_m3.exe), iWrap actor package toray (on PYTHONPATH), '
              'and the run kit run_kit (run_toray.py, run_muscle, coupling.ymmsl, input/, ci-sdcc/st03-run-actor.sh).'),
    yaml_prefix='toray',
    build_source='ci-sdcc/st01-build-code.sh',
    build_cmds=['make -f make/makefile_imas clean FC="$FC"',
                'make -j1 -f make/makefile_imas validate libtoray.a FC="$FC"',
                'make -j1 -f make/makefile_imas m3 FC="$FC"'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make -j1 -f make/makefile_imas iwrapactor FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='toray_m3.exe',
    files_to_copy=[(['toray_m3.exe'], 'bin'), (['libtoray.a', 'lib/libnag.a', 'lib/libnet.a'], 'lib'),
                   (['obj/*.mod'], 'include/toray')],
    kit_products=[('toray_m3.exe', 'toray_m3.exe')],
    kit_required=['run_toray.py', 'run_muscle', 'coupling.ymmsl', 'input/ec_waveforms.yaml',
                  'input/ec_waveforms_dd3.yaml', 'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/st03-scenario.yaml',
                  'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libtoray.a', 'run_kit/run_toray.py', 'run_kit/ci-sdcc/st03-scenario.yaml'],
    sanity_dirs=['run_kit/input'],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 134173/106 t=200 s, checks (ST03_DIR, default ./ci-st03)',
               'python run_toray.py     # iWrap actor (input/scenario[_dd3].yaml)',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    # deps.yaml names the user-tree build 14.4.0.dev1: replaced by the official 1.10.0 (same mirror-steering
    # API, ec_mirror_add_dynamic)
    cooker_map={'Waveform-Cooker/14.4.0.dev1': 'Waveform-Cooker/1.10.0-GCCcore-{gcc}'},
    cooker_note='official 1.10.0 for DD4 where deps.yaml names the user build 14.4.0.dev1: mirror steering '
                'ec_mirror_add_dynamic; 1.9.0 as in deps.yaml for DD3',
    cooker_api={'intel-2025b-dd4': 'add_dynamic, ec_mirror_add_dynamic',
                'intel-2025b-dd3': 'add_dynamic, ec_add_dynamic',
                'intel-2023b-dd3': 'add_dynamic, ec_add_dynamic'},
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
