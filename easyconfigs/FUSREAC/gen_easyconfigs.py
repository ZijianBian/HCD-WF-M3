#!/usr/bin/env python3
"""Writes the three FUSREAC easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper fusreac_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='FUSREAC', code='fusreac', helper='fusreac_run_setup',
    repo=hcd.repo('fusreac', 'FUSREAC'), prefix='fusreac',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin (no tag reachable)
    commit='5594effe39967aa54724564d269bad1437d1a41f', describe='5594eff',
    git_url='ssh://git@git.iter.org/heat', git_repo='fusreac',
    homepage='https://git.iter.org/projects/HEAT/repos/fusreac',
    summary='FUSREAC: fusion reaction rates and fusion-born particle sources (distribution_sources).',
    provides=('library libfusreac_ids.a (lib), standalone program bin/fusreac_ids, MUSCLE3 actor\n'
              'executable (bin/fusreac_m3.exe, also fusreac/fusreac_m3.exe), iWrap actor package fusreac (on\n'
              'PYTHONPATH) and the run kit (run_fusreac.py, run_muscle, coupling.ymmsl, input,\n'
              'ci-sdcc/st03-run-actor.sh);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'MUSCLE3/0.8.0-intel-2023b', 'XMLlib/3.3.2-intel-compilers-2023.2.1']),
    },
    waveform_cooker=False,
    env=[('IMAS_AL_DISABLE_OBSOLESCENT_WARNING', '1')],
    build_note='make validate, make clean, make library all DEBUG=yes, then make m3 DEBUG=yes (fusreac_m3.exe)',
    prebuild=['make validate', 'make clean DEBUG=yes FC="$FC"', 'make library all DEBUG=yes FC="$FC"'],
    target='m3', buildopts='DEBUG=yes FC="$FC"',
    files=[(['fusreac_m3.exe', 'fusreac_ids'], 'bin'),
           (['BUILD/{FC}_dd{DDMAJ}/debug/lib/libfusreac_ids.a'], 'lib')],
    actor='fusreac', actor_cmd='make actor DEBUG=yes FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='fusreac_m3.exe',
    links=[('fusreac', 'fusreac')],
    sanity_files=['bin/fusreac_ids', 'lib/libfusreac_ids.a'],
    kit_files=['fusreac_ids', 'BUILD/{FC}_dd{DDMAJ}/debug/lib/libfusreac_ids.a', 'run_fusreac.py',
               'ci-sdcc/st03-run-actor.sh', 'input/fusreac1d_param.xml'],
    stamp_code='fusreac',
    usage=['python run_fusreac.py -c input   # iWrap actor (input/scenario.yaml)',
           './run_muscle                     # MUSCLE3 actor (run_fusreac.py + fusreac_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^FUSREAC/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
