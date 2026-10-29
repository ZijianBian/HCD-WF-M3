#!/usr/bin/env python3
"""Writes the three GENRAY easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), genray_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/g/GENRAY/genray-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='GENRAY', code='genray', actor='genray', title='EC/LH/IC ray tracing',
    repo=hcd.repo('nolicense/genray', 'GENRAY'), repo_name='genray',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/genray',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='61c1f9824dde183635ce4c7f45f0881a6a584c9a', describe='10.11.3-2-g61c1f98',
    description='GENRAY general ray-tracing code for EC, LH and IC heating and current drive.',
    contents=('Fortran library (lib/libgenray_actor.a, include/genray), MUSCLE3 actor executable '
              '(bin/genray_m3.exe, also genray/genray_m3.exe), iWrap actor package genray (on PYTHONPATH), and the '
              'run kit run_kit (run_genray.py, run_muscle, coupling.ymmsl, inputs/, input_genray.xml, '
              'ci-sdcc/st03-run-actor.sh).'),
    yaml_prefix='genray',
    build_source='ci-sdcc/st01-build-code.sh',
    build_cmds=['make clean FC="$FC"', 'make -j1 libgenray_actor.a FC="$FC"', 'make -j1 m3 FC="$FC"'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make -j1 iwrapactor FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='genray_m3.exe',
    files_to_copy=[(['genray_m3.exe'], 'bin'), (['libgenray_actor.a'], 'lib'), (['*.mod'], 'include/genray')],
    kit_products=[('genray_m3.exe', 'genray_m3.exe')],
    kit_required=['run_genray.py', 'run_muscle', 'coupling.ymmsl', 'input_genray.xml', 'inputs/ec_waveforms.yaml',
                  'inputs/ec_waveforms_dd3.yaml', 'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/st03-scenario.yaml',
                  'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libgenray_actor.a', 'run_kit/run_genray.py', 'run_kit/input_genray.xml'],
    sanity_dirs=['run_kit/inputs'],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 134173/106 t=200 s, checks (ST03_DIR, default ./ci-st03)',
               'python run_genray.py    # iWrap actor (inputs/scenario[_dd3].yaml)',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    # deps.yaml names the user-tree build 14.4.0.dev1: replaced by the official 1.10.0 (same mirror-steering
    # API, ec_mirror_add_dynamic)
    cooker_map={'Waveform-Cooker/14.4.0.dev1': 'Waveform-Cooker/1.10.0-GCCcore-{gcc}'},
    cooker_note='official 1.10.0 for DD4 where deps.yaml names the user build 14.4.0.dev1: mirror steering '
                'ec_mirror_add_dynamic; 1.9.0 as in deps.yaml for DD3',
    cooker_api={'intel-2025b-dd4': 'add_dynamic, ec_mirror_add_dynamic',
                'intel-2025b-dd3': 'add_dynamic, ec_add_dynamic, ec_adjust',
                'intel-2023b-dd3': 'add_dynamic, ec_add_dynamic, ec_adjust'},
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
