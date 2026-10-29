#!/usr/bin/env python3
"""Writes the three CYRANO easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), cyrano_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/c/CYRANO/cyrano-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='CYRANO', code='cyrano', actor='cyrano', title='ICRF full-wave solver',
    repo=hcd.repo('cyrano', 'CYRANO'), repo_name='cyrano',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/cyrano',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='a1ac2d3abf78c0e8192b146c331bef87fe69c7fe', describe='1.0.0-7-ga1ac2d3',
    description='CYRANO full-wave solver for ICRF wave fields (P. U. Lamalle, PhD thesis, Universite de Mons, 1994).',
    contents=('Fortran library (lib/libcyrano_ids.a, include/cyrano), MUSCLE3 actor executable (bin/cyrano_m3.exe, '
              'also cyrano/cyrano_m3.exe, the HCD-WF pure topology path), iWrap actor package cyrano (on PYTHONPATH), '
              'and the run kit run_kit (run_cyrano.py, run_muscle, coupling.ymmsl, input/, ci-sdcc/st05-run-actor.sh). '
              'Built with DEBUG=yes as ci-sdcc/st01 + st02 (the committed iWrap yamls use the debug library).'),
    yaml_prefix='iwrap/cyrano',
    build_source='ci-sdcc/st01-build-code.sh (DEBUG=yes)',
    build_cmds=['make veryclean validate library DEBUG=yes FC="$FC"', 'make all DEBUG=yes FC="$FC"',
                'make m3 DEBUG=yes FC="$FC"'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make actor DEBUG=yes FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='cyrano_m3.exe',
    files_to_copy=[(['cyrano_m3.exe'], 'bin'), (['BUILD/debug/lib/libcyrano_ids.a'], 'lib'),
                   (['BUILD/debug/obj/*.mod'], 'include/cyrano')],
    kit_products=[('cyrano_m3.exe', 'cyrano_m3.exe')],
    kit_required=['run_cyrano.py', 'run_muscle', 'coupling.ymmsl', 'input/input_cyrano.xml',
                  'ci-sdcc/st05-run-actor.sh', 'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libcyrano_ids.a', 'run_kit/run_cyrano.py', 'run_kit/input/input_cyrano.xml'],
    sanity_dirs=['run_kit/input'],
    run_lines=['bash ci-sdcc/st05-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=200 s, ITER_MD 110000/2, checks (ST05_DIR, default ./ci-st05)',
               'python run_cyrano.py    # iWrap actor (CYRANO_INPUT_URI, CYRANO_MD_URI, CYRANO_TIME, CYRANO_OUTPUT_URI)',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    st_script='ci-sdcc/st05-run-actor.sh', st_var='ST05_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
