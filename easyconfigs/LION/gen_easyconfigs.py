#!/usr/bin/env python3
"""Writes the three LION easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), lion_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/l/LION/lion-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
COMMIT is the head of origin/feature/DD3_and_DD4 on https://gitlab.epfl.ch/spc/LION.git. The easyconfigs
use the local archive only, with its checksum (no git fallback); keep the archive in the source path.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

COMMIT = 'a0273ee820eddb67d513b0ec374fe2700f2052ed'
DESCRIBE = '2.0.0-2-ga0273ee'

CODE = dict(
    name='LION', code='lion', actor='lion', title='ICRF global full-wave code',
    repo=hcd.repo('nolicense/lion', 'LION'), repo_name='lion',
    git_base='https://gitlab.epfl.ch/spc', repo_url='https://gitlab.epfl.ch/spc/LION.git',
    homepage='https://gitlab.epfl.ch/spc/LION',
    commit=COMMIT, describe=DESCRIBE, archive_only=True,
    archive_comment='local archive only (checksum below): git archive of the commit of https://gitlab.epfl.ch/spc/LION',
    server_note=' on gitlab.epfl.ch/spc/LION',
    usage_notes=['Source: commit ' + COMMIT + ' of feature/DD3_and_DD4 on https://gitlab.epfl.ch/spc/LION'],
    description='LION global full-wave code for ion cyclotron (ICRF) heating in toroidal geometry.',
    contents=('Fortran library (lib/libLION.a, include/lion), MUSCLE3 actor executable (bin/lion_m3.exe, also '
              'lion/lion_m3.exe), iWrap actor package lion (on PYTHONPATH), and the run kit run_kit (run_lion.py, '
              'run_muscle, coupling.ymmsl, src_f90/LION_input.xml, ci-sdcc/st03-run-actor.sh). Version string '
              'V90_1_5_git_' + DESCRIBE + ' (GIT_DESCRIBE of src_f90/Makefile).'),
    yaml_prefix='lion',
    build_source='ci-sdcc/st01-build-code.sh (DEBUG=no; GIT_DESCRIBE given, the archive has no .git)',
    build_cmds=['make -C src_f90/ clean veryclean validate libraries IMAS_ENVIRONMENT_LOADED=yes DEBUG=no F90="$FC" '
                'GIT_DESCRIBE=' + DESCRIBE,
                'make -C src_f90/ m3 IMAS_ENVIRONMENT_LOADED=yes DEBUG=no F90="$FC" GIT_DESCRIBE=' + DESCRIBE],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd=('make -C src_f90/ iwrap_actor IMAS_ENVIRONMENT_LOADED=yes DEBUG=no F90="$FC" GIT_DESCRIBE=' + DESCRIBE +
               ' ACTOR_FOLDER=%(installdir)s'),
    m3='src_f90/lion_m3.exe',
    files_to_copy=[(['src_f90/lion_m3.exe'], 'bin'), (['src_f90/libLION.a'], 'lib'),
                   (['src_f90/lion_iwrap.mod'], 'include/lion')],
    kit_products=[('src_f90/lion_m3.exe', 'src_f90/lion_m3.exe')],
    kit_required=['run_lion.py', 'run_muscle', 'coupling.ymmsl', 'src_f90/LION_input.xml',
                  'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libLION.a', 'run_kit/run_lion.py', 'run_kit/src_f90/LION_input.xml'],
    sanity_dirs=[],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/4 t=198.25 s, ITER_MD 110000/2, checks (ST03_DIR, default ./ci-st03)',
               'python run_lion.py      # iWrap actor (LION_INPUT_URI, LION_MD_URI, LION_TIME, LION_OUTPUT_URI)',
               './run_muscle            # MUSCLE3 actor (coupling.ymmsl)'],
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
