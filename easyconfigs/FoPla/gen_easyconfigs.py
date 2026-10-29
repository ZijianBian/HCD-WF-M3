#!/usr/bin/env python3
"""Writes the three FoPla easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper fopla_run_setup.sh
and the source archive (git archive of the pinned commit) through ../_lib/hcd_ec.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='FoPla', code='fopla', helper='fopla_run_setup',
    repo=hcd.repo('fopla', 'FoPla'), prefix='fopla',
    # origin/feature/DD3_and_DD4, verified 2026-10-26 after git fetch origin
    commit='1aa9da05b40b334d2f66abe01c57d3aa1c79ad54', describe='2.1.0-34-g1aa9da0',
    git_url='ssh://git@git.iter.org/heat', git_repo='fopla',
    homepage='https://git.iter.org/projects/HEAT/repos/fopla',
    summary='FoPla: Fokker-Planck solver for ICRF/NBI fast-ion distributions.',
    provides=('library libFoPla_icrh_ids.a (lib), MUSCLE3 actor executable (bin/fopla_m3.exe, also\n'
              'fopla/fopla_m3.exe), iWrap actor package fopla (on PYTHONPATH) and the run kit (run_fopla,\n'
              'run_muscle, coupling.ymmsl, input, ci-sdcc/st03-run-actor.sh with its test entry\n'
              'ci-sdcc/st03-imasdb);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'MUSCLE3/0.10.0-intel-2025b', 'XMLlib/3.3.2-intel-compilers-2025.2.0']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'MUSCLE3/0.8.0-intel-2023b', 'XMLlib/3.3.2-intel-compilers-2023.2.1']),
    },
    waveform_cooker=True,
    build_note='make veryclean validate clean library DEBUG=yes, then make m3 DEBUG=yes (fopla_m3.exe)',
    prebuild=['make veryclean validate clean library DEBUG=yes FC="$FC"'],
    target='m3', buildopts='DEBUG=yes FC="$FC"',
    files=[(['fopla_m3.exe'], 'bin'), (['BUILD/debug/lib/libFoPla_icrh_ids.a'], 'lib')],
    actor='fopla', actor_cmd='make iwrap_actor DEBUG=yes FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='fopla_m3.exe',
    links=[('fopla', 'fopla')],
    sanity_files=['lib/libFoPla_icrh_ids.a'],
    kit_files=['BUILD/debug/lib/libFoPla_icrh_ids.a', 'run_fopla', 'ci-sdcc/st03-run-actor.sh',
               'ci-sdcc/st03-scenario.yaml', 'ci-sdcc/st03-imasdb/ITER/4/130012/100/master.h5',
               'input/input_FoPla_icrh_only.xml'],
    py_check='import waveform_cooker, ymmsl, libmuscle',
    stamp_code='fopla',
    usage=['python run_fopla -c input   # iWrap actor (input/scenario.yaml)',
           './run_muscle                # MUSCLE3 actor (run_fopla + fopla_m3.exe)',
           'MODULES=$(module -t list 2>&1 | grep ^FoPla/) bash ci-sdcc/st03-run-actor.sh   # CI case'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
