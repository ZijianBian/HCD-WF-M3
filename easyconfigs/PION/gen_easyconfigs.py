#!/usr/bin/env python3
"""Writes the three PION easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper pion_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='PION', code='pion', helper='pion_run_setup',
    repo=hcd.repo('pion', 'PION'), prefix='pion',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin
    commit='69bf1b6e98a1f3e0505e53ed040f2c56ebbf7cc6', describe='2.1.0-5-g69bf1b6',
    git_url='ssh://git@git.iter.org/heat', git_repo='pion',
    homepage='https://git.iter.org/projects/HEAT/repos/pion',
    summary='PION ICRF heating code (ICRH power deposition and fast-ion distribution).',
    provides=('library pimascal.a (lib, include/pion), MUSCLE3 actor executable (bin/pion_m3.exe, also\n'
              'pion/pion_m3.exe), iWrap actor package pion (on PYTHONPATH) and the run kit (run_pion.py,\n'
              'run_muscle, coupling.ymmsl, input, ci-sdcc/st03-run-actor.sh);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0',
            'INTERPOS/9.2.3-iimkl-2025b', 'NAG/26-intel-compilers-2025.2.0']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0',
            'INTERPOS/9.2.3-iimkl-2025b', 'NAG/26-intel-compilers-2025.2.0']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'MUSCLE3/0.8.0-intel-2023b', 'XMLlib/3.3.2-intel-compilers-2023.2.1',
            'INTERPOS/9.2.0-iimkl-2023b', 'NAG/26-intel-compilers-2023.2.1']),
    },
    toolchainopts={'rpath': False},
    toolchainopts_comment=('No RPATH wrappers: with them, make m3 fails to link against the MKL bundled with NAG/26 '
                           '(libmkl_def.so: undefined mkl_sparse_* symbols).'),
    waveform_cooker=True,
    env=[('IMASFORPION', 'DIMAS_LATEST')],
    build_note='make clean veryclean, make pimascal.a, then make m3 (pion_m3.exe)',
    prebuild=['make clean veryclean FC="$FC"', 'make pimascal.a FC="$FC"'],
    target='m3', buildopts='FC="$FC"',
    files=[(['pion_m3.exe'], 'bin'), (['pimascal.a'], 'lib'), (['fortran_imas/*.mod'], 'include/pion')],
    actor='pion', actor_cmd='make iwrap_actor FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='pion_m3.exe',
    links=[('pion', 'pion')],
    sanity_files=['lib/pimascal.a', 'include/pion/pion_iwrap.mod'],
    kit_files=['pimascal.a', 'fortran_imas/pion_iwrap.mod', 'run_pion.py', 'dd_compat.py',
               'ci-sdcc/st03-run-actor.sh', 'input/input_pion.xml'],
    py_check='import waveform_cooker, ymmsl, libmuscle',
    stamp_code='pion',
    usage=['python run_pion.py -c input    # iWrap actor (input/scenario.yaml, PION_* variables)',
           './run_muscle                   # MUSCLE3 actor (run_pion.py + pion_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^PION/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
