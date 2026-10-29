#!/usr/bin/env python3
"""Writes the three TORIC easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper toric_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

# OPT= on every make call: config/ITER_SDCC.mk adds -fast (-xHost -ipo with the Intel compilers)
# when OPT=fast; the module is shared on all node types, so this branch stays off.
CODE = dict(
    name='TORIC', code='toric', helper='toric_run_setup',
    repo=hcd.repo('toric', 'TORIC'), prefix='toric',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin
    commit='43393d2cfdabfc8e69e2cc51bee1f85cfb689349', describe='before_ggd_generalisation-4-g43393d2',
    git_url='ssh://git@git.iter.org/heat', git_repo='toric',
    homepage='https://git.iter.org/projects/HEAT/repos/toric',
    summary='TORIC full-wave ICRF code (ion cyclotron wave propagation and absorption).',
    provides=('library libtoric.a and the in-tree GGD library libimas_ggd.a (lib, include/toric),\n'
              'MUSCLE3 actor executable (bin/toric_m3.exe, also toric/toric_m3.exe), iWrap actor package\n'
              'toric (on PYTHONPATH) and the run kit (run_toric.py, run_muscle, coupling.ymmsl, xml, input,\n'
              'ci-sdcc/st03-run-actor.sh; without tests/ and doc/);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0',
            'netCDF-Fortran/4.6.2-iimpi-2025b', 'imkl-FFTW/2025.2.0-iimpi-2025b']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0',
            'netCDF-Fortran/4.6.2-iimpi-2025b', 'imkl-FFTW/2025.2.0-iimpi-2025b']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'MUSCLE3/0.8.0-intel-2023b', 'XMLlib/3.3.2-intel-compilers-2023.2.1',
            'netCDF-Fortran/4.6.1-iimpi-2023b', 'imkl-FFTW/2023.2.0-iimpi-2023b']),
    },
    waveform_cooker=True,
    build_note='make veryclean, make library (libtoric.a, grid_library), then make m3 (toric_m3.exe); OPT= keeps -fast off',
    prebuild=['make veryclean OPT=', 'make library OPT='],
    target='m3', buildopts='OPT=',
    files=[(['toric_m3.exe'], 'bin'),
           (['bin/Linux/Ser/libtoric.a', 'grid_library/{FC}/lib/libimas_ggd.a'], 'lib'),
           (['bin/Linux/Ser/*.mod'], 'include/toric')],
    actor='toric', actor_cmd='make actor OPT= ACTOR_FOLDER=%(installdir)s',
    m3='toric_m3.exe',
    links=[('toric', 'toric')],
    kit_exclude=['./tests', './doc'],
    sanity_files=['lib/libtoric.a', 'lib/libimas_ggd.a', 'include/toric/t6_mod_itmtoric.mod'],
    kit_files=['bin/Linux/Ser/libtoric.a', 'grid_library/{FC}/lib/libimas_ggd.a', 'run_toric.py',
               'ci-sdcc/st03-run-actor.sh', 'xml/toricainp.xml'],
    py_check='import waveform_cooker, ymmsl, libmuscle',
    stamp_code='toric',
    usage=['python run_toric.py -c input   # iWrap actor (input/scenario.yaml, TORIC_* variables)',
           './run_muscle                   # MUSCLE3 actor (run_toric.py + toric_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^TORIC/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
