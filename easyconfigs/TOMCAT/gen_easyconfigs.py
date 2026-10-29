#!/usr/bin/env python3
"""Writes the three TOMCAT easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), tomcat_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/t/TOMCAT/tomcat-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='TOMCAT', code='tomcat', actor='tomcat', title='ICRF 1D full-wave solver',
    repo=hcd.repo('tomcat', 'TOMCAT'), repo_name='tomcat',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/tomcat',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='50129f7d88e0436874beaa252f4edc4646d943b4', describe='1.0.0-2-g50129f7',
    description='TOMCAT one-dimensional full-wave code for ion cyclotron (ICRF) heating.',
    contents=('Fortran library (lib/libtomcat.a, include/tomcat), MUSCLE3 actor executable (bin/tomcat_m3.exe, also '
              'tomcat/tomcat_m3.exe), iWrap actor package tomcat (on PYTHONPATH), and the run kit run_kit '
              '(run_tomcat.py, run_muscle, coupling.ymmsl, input/, ci-sdcc/st03-run-actor.sh).'),
    yaml_prefix='tomcat',
    build_source='ci-sdcc/st01-build-code.sh (DEBUG=no)',
    build_cmds=['make -C fortran_sources/ clean library DEBUG=no FC="$FC"', 'make -C fortran_sources/ m3 DEBUG=no FC="$FC"'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make -C fortran_sources/ iwrap_actor DEBUG=no FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='tomcat_m3.exe',
    files_to_copy=[(['tomcat_m3.exe'], 'bin'), (['fortran_sources/obj/libtomcat.a'], 'lib'),
                   (['fortran_sources/obj/*.mod'], 'include/tomcat')],
    kit_products=[('tomcat_m3.exe', 'tomcat_m3.exe')],
    kit_required=['run_tomcat.py', 'run_muscle', 'coupling.ymmsl', 'input/tomcat.xml',
                  'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/build_stamp.sh', 'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/libtomcat.a', 'run_kit/run_tomcat.py', 'run_kit/input/tomcat.xml'],
    sanity_dirs=['run_kit/input'],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on ITER 130012/5 t=200 s, checks (ST03_DIR, default ./ci-st03)',
               'python run_tomcat.py --src <uri> --dest <uri> --time <t> -cp input/tomcat.xml   # iWrap actor',
               './run_muscle [settings.ymmsl]   # MUSCLE3 actor (coupling.ymmsl)'],
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
