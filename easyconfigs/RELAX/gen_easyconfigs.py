#!/usr/bin/env python3
"""Writes the three RELAX easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), relax_run_setup.sh,
resolve_deps_module.sh and test_module.sh next to this script, and the source archive
<work>/sources/r/RELAX/relax-<VERSION>.tar.gz (git archive of COMMIT from the local clone).
Rerun after editing this file or ../_lib/hcd_ec.py (checksums of the helpers are computed here).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='RELAX', code='relax', actor='relax', title='quasi-linear Fokker-Planck for EC current drive',
    repo=hcd.repo('relax', 'RELAX'), repo_name='relax',
    git_base='ssh://git@git.iter.org/heat',
    homepage='https://git.iter.org/projects/HEAT/repos/relax',
    # origin/feature/DD3_and_DD4 (local HEAD == origin, 0/0, fetched 2026-10-22)
    commit='36011ca6c6dfd416c6f035f6e7231c8f53480a74', describe='1.0.0-4-g36011ca',
    description='RELAX quasi-linear relativistic Fokker-Planck code for electron cyclotron current drive.',
    contents=('Fortran library (lib/librelax.a with lib/libnag.a, lib/libnet.a, lib/libppp.a, include/relax), '
              'MUSCLE3 actor executable (bin/relax_m3.exe, also relax/relax_m3.exe), iWrap actor package relax (on '
              'PYTHONPATH), and the run kit run_kit (run_relax.py, run_muscle, coupling.ymmsl, input/, '
              'tests/toray_134173_106, ci-sdcc/st03-run-actor.sh).'),
    yaml_prefix='relax',
    build_source='build.sh (the targets of ci-sdcc/st01-build-code.sh)',
    build_cmds=['make -f make/makefile_imas FC="$FC" clean', 'make -f make/makefile_imas FC="$FC" libs librelax.a',
                'make -f make/makefile_imas FC="$FC" m3'],
    iwrap_source='ci-sdcc/st02-build-actor.sh',
    iwrap_cmd='make -f make/makefile_imas FC="$FC" actor ACTOR_FOLDER=%(installdir)s',
    m3='relax_m3.exe',
    files_to_copy=[(['relax_m3.exe'], 'bin'), (['librelax.a', 'lib/libnag.a', 'lib/libnet.a', 'lib/libppp.a'], 'lib'),
                   (['obj/*.mod'], 'include/relax')],
    kit_products=[('relax_m3.exe', 'relax_m3.exe')],
    kit_required=['run_relax.py', 'run_muscle', 'coupling.ymmsl', 'tests/toray_134173_106/make_input.py',
                  'tests/toray_134173_106/scenario.yaml', 'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/build_stamp.sh',
                  'ci-sdcc/st00-header.sh'],
    sanity_files=['lib/librelax.a', 'run_kit/run_relax.py', 'run_kit/tests/toray_134173_106/make_input.py'],
    sanity_dirs=['run_kit/input'],
    run_lines=['bash ci-sdcc/st03-run-actor.sh   # CI case: iWrap + MUSCLE3 actor on tests/toray_134173_106 (input from ITER 134173/106), checks (ST03_DIR, default ./ci-st03)',
               'python run_relax.py -c <config folder>   # iWrap actor',
               './run_muscle -c <config folder>          # MUSCLE3 actor (coupling.ymmsl)'],
    cooker_note='1.9.0 as in deps.yaml of the commit',
    cooker_api={c: 'ec_add_dynamic' for c in hcd.FLAVOURS},
    st_script='ci-sdcc/st03-run-actor.sh', st_var='ST03_DIR',
)

if __name__ == '__main__':
    hcd.generate(CODE, HERE)
