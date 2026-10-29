#!/usr/bin/env python3
"""Writes the three StixReDist easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper
stixredist_run_setup.sh and the source archive (git archive of the pinned commit) through
../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='StixReDist', code='stixredist', helper='stixredist_run_setup',
    repo=hcd.repo('nolicense/stixredist', 'StixReDist'), prefix='stixredist',
    # origin/feature/DD3_and_DD4, verified 2026-10-22 after git fetch origin
    commit='750c24c8d05d34f5946f9b8d0f4e97a4a98edfd8', describe='2.1.0-7-g750c24c',
    git_url='ssh://git@git.iter.org/heat', git_repo='stixredist',
    homepage='https://git.iter.org/projects/HEAT/repos/stixredist',
    summary='StixReDist: ICRF quasi-linear redistribution of fast ions (Stix model).',
    provides=('library libstix_redist_ids.a (lib), MUSCLE3 actor executable (bin/stixredist_m3.exe,\n'
              'also stix_redist/stixredist_m3.exe), iWrap actor package stix_redist (on PYTHONPATH) and the\n'
              'run kit (run_stix_redist, run_muscle, coupling.ymmsl, input, ci-sdcc/st03-run-actor.sh with\n'
              'its test entry ci-sdcc/st03-imasdb);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'MUSCLE3/0.8.0-intel-2023b', 'XMLlib/3.3.2-intel-compilers-2023.2.1']),
    },
    waveform_cooker=True,
    build_note='make veryclean validate library DEBUG=yes, then make m3 DEBUG=yes (stixredist_m3.exe)',
    prebuild=['make veryclean validate library DEBUG=yes FC="$FC"'],
    target='m3', buildopts='DEBUG=yes FC="$FC"',
    files=[(['stixredist_m3.exe'], 'bin'), (['BUILD/debug/lib/libstix_redist_ids.a'], 'lib')],
    actor='stix_redist', actor_cmd='make iwrap_actor DEBUG=yes FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='stixredist_m3.exe',
    links=[('stix_redist', 'stix_redist')],
    sanity_files=['lib/libstix_redist_ids.a'],
    kit_files=['BUILD/debug/lib/libstix_redist_ids.a', 'run_stix_redist', 'ci-sdcc/st03-run-actor.sh',
               'ci-sdcc/st03-scenario.yaml', 'ci-sdcc/st03-imasdb/ITER/4/130012/100/master.h5',
               'input/stix_redist.xml'],
    py_check='import waveform_cooker, ymmsl, libmuscle',
    stamp_code='stixredist',
    usage=['python run_stix_redist -c input   # iWrap actor (input/scenario.yaml)',
           './run_muscle                      # MUSCLE3 actor (run_stix_redist + stixredist_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^StixReDist/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
