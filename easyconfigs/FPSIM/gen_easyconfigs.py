#!/usr/bin/env python3
"""Writes the three FPSIM easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b; actor iccoup), fpsim_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/f/FPSIM/fpsim-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='FPSIM', code='fpsim', actor='iccoup', title='IC antenna coupling ICCOUP',
    repo=hcd.repo('nolicense/fpsim', 'FPSIM'), repo_name='fpsim',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/fpsim',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='821b314b3a5dbc2fd4f208973b984d7045db2e9e', describe='1.0.0-2-g821b314',
    description='FPSIM fast particle simulation tools: ICCOUP ion cyclotron antenna coupling (toroidal mode spectrum).',
    contents=('ICCOUP Fortran library (lib/libiccoup_debug.a, include/iccoup), MUSCLE3 actor executable '
              '(bin/iccoup_m3.exe, also iccoup/iccoup_m3.exe), iWrap actor package iccoup (on PYTHONPATH), and the '
              'run kit run_kit (run_iccoup.py, run_muscle, coupling.ymmsl, tools/iccoup/input, '
              'ci-sdcc/st03-run-actor.sh). Built with DEBUG=yes as ci-sdcc/st01 + st02 (the committed iWrap yamls '
              'use the debug library); the build runs the standalone check prog_ids_iccoup.exe of st01.'),
    yaml_prefix='tools/iccoup',
    build_source='ci-sdcc/st01-build-code.sh (DEBUG=yes, with the standalone check)',
    build_cmds=['make -C tools/iccoup/ DEBUG=yes veryclean library FC="$FC"',
                'make -C tools/iccoup/ DEBUG=yes check FC="$FC"',
                'make -C tools/iccoup/ DEBUG=yes m3 FC="$FC"'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make -C tools/iccoup/ DEBUG=yes iwrap_actor FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='tools/iccoup/iccoup_m3.exe',
    files_to_copy=[(['tools/iccoup/iccoup_m3.exe'], 'bin'), (['tools/iccoup/lib/{fc}_debug/libiccoup_debug.a'], 'lib'),
                   (['tools/iccoup/obj/{fc}_debug/*.mod'], 'include/iccoup')],
    kit_products=[('tools/iccoup/iccoup_m3.exe', 'tools/iccoup/iccoup_m3.exe')],
    kit_required=['run_iccoup.py', 'run_muscle', 'coupling.ymmsl', 'tools/iccoup/input/input_iccoup.xml',
                  'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libiccoup_debug.a', 'run_kit/run_iccoup.py', 'run_kit/tools/iccoup/input/input_iccoup.xml'],
    sanity_dirs=['run_kit/tools/iccoup/input'],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=200 s, ITER_MD 110000/2, checks (ST03_DIR, default ./ci-st03)',
               'python run_iccoup.py    # iWrap actor (ICCOUP_INPUT_URI, ICCOUP_MD_URI, ICCOUP_TIME, ICCOUP_OUTPUT_URI)',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
