#!/usr/bin/env python3
"""Writes the three HCD2CORE_SOURCES easyconfigs (DD4/2025b, DD3/2025b, DD3/2023b), the helper
hcd2core_sources_run_setup.sh and the source archive (git archive of the pinned commit) through
../_lib/hcd_ec.py. The module name HCD2CORE_SOURCES is the official one; the date-label
versions <VERSION>-intel-<tc>-DD-<dd> are not used by the site tree."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '_lib'))
import hcd_ec as hcd  # noqa: E402

CODE = dict(
    name='HCD2CORE_SOURCES', code='hcd2core-sources', helper='hcd2core_sources_run_setup',
    repo=hcd.repo('hcd2core-sources', 'HCD2CORE_SOURCES'), prefix='hcd2core-sources',
    # origin/feature/DD3_and_DD4, verified 2026-10-27 after git fetch origin
    commit='8bbc4f3d2fa9083bb3a7c29645804088e1f9415a', describe='1.2.0-36-g8bbc4f3',
    git_url='ssh://git@git.iter.org/heat', git_repo='hcd2core-sources',
    homepage='https://git.iter.org/projects/HEAT/repos/hcd2core-sources',
    summary='hcd2core_sources: conversion of waves, distributions and distribution_sources into core_sources.',
    provides=('library libhcd2core_sources.a (lib, include/hcd2core_sources), MUSCLE3 actor executable\n'
              '(bin/hcd2core_sources_m3.exe, also hcd2core_sources/hcd2core_sources_m3.exe, the path used by\n'
              'HCD-WF), iWrap actor package hcd2core_sources (on PYTHONPATH) and the run kit\n'
              '(run_hcd2core_sources.py, run_muscle, coupling.ymmsl, input);'),
    flavours={
        'intel-2025b-dd4': dict(modules=hcd.BASE_2025B_DD4 + [
            'IDStools/2.5.0-intel-2025b', 'MUSCLE3/0.10.0-intel-2025b',
            'XMLlib/3.3.2-intel-compilers-2025.2.0', 'INTERPOS/9.2.3-iimkl-2025b',
            'Fundamental-Constants/0.2.1']),
        'intel-2025b-dd3': dict(modules=hcd.BASE_2025B_DD3 + [
            'IDStools/2.5.0-intel-2025b', 'MUSCLE3/0.10.0-intel-2025b',
            'XMLlib/3.3.2-intel-compilers-2025.2.0', 'INTERPOS/9.2.3-iimkl-2025b',
            'Fundamental-Constants/0.2.1']),
        'intel-2023b-dd3': dict(modules=hcd.BASE_2023B_DD3 + [
            'IDStools/2.5.0-intel-2023b', 'MUSCLE3/0.8.0-intel-2023b',
            'XMLlib/3.3.2-intel-compilers-2023.2.1', 'INTERPOS/9.2.0-iimkl-2023b',
            'Fundamental-Constants/0.2.1']),
    },
    waveform_cooker=False,
    build_note='make -C src/ veryclean info library DEBUG=yes, then make -C src/ m3 (build.sh)',
    prebuild=['make -C src/ veryclean info library DEBUG=yes FC="$FC"'],
    target='-C src/ m3', buildopts='DEBUG=yes FC="$FC"',
    files=[(['src/hcd2core_sources_m3.exe'], 'bin'),
           (['src/build/lib/debug/libhcd2core_sources.a'], 'lib'),
           (['src/build/obj/debug/*.mod'], 'include/hcd2core_sources')],
    actor='hcd2core_sources', actor_cmd='make -C src/ iwrapactor DEBUG=yes FC="$FC" ACTOR_FOLDER=%(installdir)s',
    m3='src/hcd2core_sources_m3.exe',
    links=[('hcd2core_sources', 'hcd2core_sources')],
    sanity_files=['lib/libhcd2core_sources.a', 'include/hcd2core_sources/hcd2core_sources_module.mod'],
    kit_files=['src/build/lib/debug/libhcd2core_sources.a', 'run_hcd2core_sources.py', 'input/scenario.yaml',
               'input/codeparam_hcd2core_source.xml'],
    stamp_code='hcd2core-sources',
    usage=['python run_hcd2core_sources.py   # iWrap actor (input/scenario.yaml: set output_user_or_path)',
           './run_muscle                     # MUSCLE3 actor (run_hcd2core_sources.py + src/hcd2core_sources_m3.exe)'],
)

if __name__ == '__main__':
    hcd.write_spec(CODE, HERE)
