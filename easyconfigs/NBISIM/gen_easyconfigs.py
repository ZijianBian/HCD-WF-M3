#!/usr/bin/env python3
"""Writes the three NBISIM easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper nbisim_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

OPTS = 'DATAMODEL=IMAS DEBUG=yes FC="$FC" SVNVERSION=unknown SVNURL=unknown SVNROOT=unknown'

CODE = dict(
    name='NBISIM', code='nbisim', helper='nbisim_run_setup',
    repo=hcd.repo('nolicense/nbisim', 'NBISIM'), prefix='nbisim',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin
    commit='1980312b6d26210bdd113d15ccdcaa26dd23a976', describe='1.3.0-2-g1980312',
    git_url='ssh://git@git.iter.org/heat', git_repo='nbisim',
    homepage='https://git.iter.org/projects/HEAT/repos/nbisim',
    summary='NBISIM: neutral beam injection fast-ion slowing-down code.',
    provides=('library libnbisim2.a (lib, include/nbisim), MUSCLE3 actor executable (bin/nbisim_m3.exe,\n'
              'also nbisim/nbisim_m3.exe), iWrap actor package nbisim (on PYTHONPATH) and the run kit\n'
              '(run_nbisim.py, run_muscle, coupling.ymmsl, input, ci-sdcc/st03-run-actor.sh);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0',
            'INTERPOS/9.2.3-iimkl-2025b']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0',
            'INTERPOS/9.2.3-iimkl-2025b']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'MUSCLE3/0.8.0-intel-2023b', 'XMLlib/3.3.2-intel-compilers-2023.2.1',
            'INTERPOS/9.2.0-iimkl-2023b']),
    },
    waveform_cooker=False,
    build_note='make -C devel/ veryclean veryclean-deps, make -C devel/ (libnbisim2.a), then make -C devel/ m3 (nbisim_m3.exe)',
    prebuild=['make -C devel/ veryclean veryclean-deps DATAMODEL=IMAS DEBUG=yes FC="$FC"', 'make -C devel/ ' + OPTS],
    target='-C devel/ m3', buildopts=OPTS,
    files=[(['nbisim_m3.exe'], 'bin'),
           (['devel/BUILD/IMAS/{FC}/debug/lib/libnbisim2.a'], 'lib'),
           (['devel/BUILD/IMAS/{FC}/debug/mod/imas_nbisim.mod'], 'include/nbisim')],
    actor='nbisim', actor_cmd='make -C devel/ iwrap_actor ' + OPTS + ' ACTOR_FOLDER=%(installdir)s',
    m3='nbisim_m3.exe',
    links=[('devel/nbisim', 'nbisim')],
    sanity_files=['lib/libnbisim2.a', 'include/nbisim/imas_nbisim.mod'],
    kit_files=['devel/BUILD/IMAS/{FC}/debug/lib/libnbisim2.a', 'run_nbisim.py', 'ci-sdcc/st03-run-actor.sh',
               'ci-sdcc/st03-scenario.yaml', 'input/input_nbisim2.xml'],
    stamp_code='nbisim',
    usage=['python run_nbisim.py -c input   # iWrap actor (input/scenario.yaml)',
           './run_muscle                    # MUSCLE3 actor (run_nbisim.py + nbisim_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^NBISIM/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
