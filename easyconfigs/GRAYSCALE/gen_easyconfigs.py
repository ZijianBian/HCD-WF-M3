#!/usr/bin/env python3
"""Writes the three GRAYSCALE easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), grayscale_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/g/GRAYSCALE/grayscale-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='GRAYSCALE', code='grayscale', actor='grayscale', title='EC current drive scaling',
    repo=hcd.repo('grayscale', 'GRAYSCALE'), repo_name='grayscale',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/grayscale',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='9515ef3893aa9acf9f1aa0802881ab449c7f1bee', describe='1.1.0-18-g9515ef3',
    description='GRAYSCALE: fast EC heating and current drive deposition from GRAY-based scaling laws.',
    contents=('Fortran library (lib/libgrayscale_debug.a, include/grayscale), MUSCLE3 actor executable '
              '(bin/grayscale_m3.exe, also grayscale/grayscale_m3.exe), iWrap actor package grayscale (on PYTHONPATH), '
              'and the run kit run_kit (run_grayscale.py, run_muscle, coupling.ymmsl, input/, ci-sdcc/st03-run-actor.sh). '
              'Built with DEBUG=yes as ci-sdcc/st01 + st02 (the committed iWrap yamls use the debug library).'),
    yaml_prefix='grayscale',
    build_source='ci-sdcc/st01-build-code.sh (DEBUG=yes)',
    build_cmds=['make clean library FC="$FC" DEBUG=yes', 'make m3 FC="$FC" DEBUG=yes'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make iwrap_actor FC="$FC" DEBUG=yes ACTOR_FOLDER=%(installdir)s',
    m3='grayscale_m3.exe',
    files_to_copy=[(['grayscale_m3.exe'], 'bin'), (['lib/{fc}_debug/libgrayscale_debug.a'], 'lib'),
                   (['obj/{fc}_debug/*.mod'], 'include/grayscale')],
    kit_products=[('grayscale_m3.exe', 'grayscale_m3.exe')],
    kit_required=['run_grayscale.py', 'run_muscle', 'coupling.ymmsl', 'input/input_file.xml',
                  'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libgrayscale_debug.a', 'run_kit/run_grayscale.py', 'run_kit/input/input_file.xml'],
    sanity_dirs=['run_kit/input'],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/5, checks (ST03_DIR, default ./ci-st03)',
               'python run_grayscale.py --src <uri> --dest <uri> --time <t>   # iWrap actor',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
