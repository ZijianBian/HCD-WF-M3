#!/usr/bin/env python3
"""Writes the three NEMO easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper nemo_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='NEMO', code='nemo', helper='nemo_run_setup',
    repo=hcd.repo('nemo', 'NEMO'), prefix='nemo',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin
    commit='c8fbe1605e3a60758f8f393d3d0931f45018ac2a', describe='2.2.0-12-gc8fbe16',
    git_url='ssh://git@git.iter.org/heat', git_repo='nemo',
    homepage='https://git.iter.org/projects/HEAT/repos/nemo',
    summary='NEMO: NBI ionisation and fast-ion source code (with the in-tree grid_library).',
    provides=('library libnemo.a (lib, with the FRUIT test hooks of USE_FRUIT=yes), MUSCLE3 actor\n'
              'executable (bin/nemo_m3.exe, also nemo/nemo_m3.exe), iWrap actor package nemo (on PYTHONPATH)\n'
              'and the run kit (run_nemocode, run_nemo, run_muscle, coupling.ymmsl, input,\n'
              'ci-sdcc/st03-run-actor.sh, ci-sdcc/st05-run-actor.sh);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'IDStools/2.5.0-intel-2025b', 'MUSCLE3/0.10.0-intel-2025b',
            'XMLlib/3.3.2-intel-compilers-2025.2.0', 'INTERPOS/9.2.3-iimkl-2025b']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'IDStools/2.5.0-intel-2025b', 'MUSCLE3/0.10.0-intel-2025b',
            'XMLlib/3.3.2-intel-compilers-2025.2.0', 'INTERPOS/9.2.3-iimkl-2025b']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'IDStools/2.5.0-intel-2023b', 'MUSCLE3/0.8.0-intel-2023b',
            'XMLlib/3.3.2-intel-compilers-2023.2.1', 'INTERPOS/9.2.0-iimkl-2023b']),
    },
    waveform_cooker=True,
    build_note='make DEBUG=yes USE_FRUIT=yes clean validate library m3 (libnemo.a, nemo_m3.exe)',
    prebuild=[],
    target='clean validate library m3', buildopts='DEBUG=yes USE_FRUIT=yes FCOMPILER="$FC"',
    files=[(['nemo_m3.exe'], 'bin'), (['libnemo.a'], 'lib')],
    actor='nemo', actor_cmd='make actor DEBUG=yes USE_FRUIT=yes FCOMPILER="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='nemo_m3.exe',
    links=[('nemo', 'nemo')],
    sanity_files=['lib/libnemo.a'],
    kit_files=['obj_{FC}/libnemo.a', 'run_nemocode', 'run_nemo', 'dd_compat.py', 'ci-sdcc/st03-run-actor.sh',
               'input/input_nemo_reg.xml', 'input/scenario.yaml'],
    py_check='import waveform_cooker, ymmsl, libmuscle',
    stamp_code='nemo',
    usage=['python run_nemo -c input   # iWrap actor (input/scenario.yaml)',
           './run_muscle               # MUSCLE3 actor (run_nemo + nemo_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^NEMO/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
