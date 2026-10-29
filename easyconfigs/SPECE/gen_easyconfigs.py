#!/usr/bin/env python3
"""Writes the three SPECE easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper spece_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='SPECE', code='spece', helper='spece_run_setup',
    repo=hcd.repo('spece', 'SPECE'), prefix='spece',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin (no tag reachable)
    commit='29c32934c6777d167098ef9ce2fd7fa938523a53', describe='29c3293',
    git_url='ssh://git@git.iter.org/diag', git_repo='spece',
    homepage='https://git.iter.org/projects/DIAG/repos/spece',
    summary='SPECE: synthetic electron cyclotron emission diagnostic (ece IDS).',
    provides=('library libspece.a (lib, include/spece), standalone program bin/spece, MUSCLE3 actor\n'
              'executable (bin/spece_m3.exe, also spece/spece_m3.exe), iWrap actor package spece (on\n'
              'PYTHONPATH) and the run kit (run_spece, run_muscle, coupling.ymmsl, input,\n'
              'ci-sdcc/st03-run-actor.sh);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'IDStools/2.5.0-intel-2025b', 'MUSCLE3/0.10.0-intel-2025b',
            'XMLlib/3.3.2-intel-compilers-2025.2.0', 'INTERPOS/9.2.3-iimkl-2025b'],
            links=[('spece_dd4/spece', 'spece')]),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'IDStools/2.5.0-intel-2025b', 'MUSCLE3/0.10.0-intel-2025b',
            'XMLlib/3.3.2-intel-compilers-2025.2.0', 'INTERPOS/9.2.3-iimkl-2025b'],
            links=[('spece_dd3_2025b/spece', 'spece')]),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'IDStools/2.5.0-intel-2023b', 'MUSCLE3/0.8.0-intel-2023b',
            'XMLlib/3.3.2-intel-compilers-2023.2.1', 'INTERPOS/9.2.0-iimkl-2023b'],
            links=[('spece_dd3_2023b/spece', 'spece')]),
    },
    waveform_cooker=False,
    env=[('IMAS_AL_DISABLE_OBSOLESCENT_WARNING', '1')],
    build_note='make clean, make -j1 spece libspece.a, then make m3 (spece_m3.exe)',
    prebuild=['make clean FC="$FC"', 'make -j1 spece libspece.a FC="$FC"'],
    target='m3', buildopts='FC="$FC"',
    files=[(['spece_m3.exe', 'spece'], 'bin'), (['libspece.a'], 'lib'), (['*.mod'], 'include/spece')],
    actor='spece', actor_cmd='make actor FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='spece_m3.exe',
    sanity_files=['bin/spece', 'lib/libspece.a'],
    kit_files=['spece', 'libspece.a', 'run_spece', 'ci-sdcc/st03-run-actor.sh', 'ci-sdcc/st03-scenario.yaml',
               'input/input_spece.xml'],
    stamp_code='spece',
    usage=['python run_spece -c input   # iWrap actor (input/scenario.yaml)',
           './run_muscle                # MUSCLE3 actor (run_spece + spece_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^SPECE/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
