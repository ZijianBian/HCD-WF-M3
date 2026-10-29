"""Generator library of the H&CD actor easyconfigs (one gen_easyconfigs.py per code folder).

Layout (relative to the HCD-WF repository):
  easyconfigs/_lib/hcd_ec.py          this library
  easyconfigs/_lib/run_setup.sh.in    template of the <code>_run_setup helpers
  easyconfigs/_lib/test_lib.sh        functions sourced by the test_module.sh scripts
  easyconfigs/sources.sha256          sha256 of the source archives (paths relative to the sources dir)
  easyconfigs/<NAME>/gen_easyconfigs.py  code data (pinned commit, deps, build commands, kit, test)
  easyconfigs/<NAME>/<NAME>-<VERSION>-intel-<tc>-DD-<dd>.eb  generated, committed

A gen_easyconfigs.py writes the three easyconfigs, the run-directory helper and (for some codes) the
test script next to itself, and the source archive <work>/sources/<letter>/<NAME>/<namelower>-<VERSION>.tar.gz
(git archive of the pinned commit, read-only on the clone, written only when missing, checked against
sources.sha256). With --sources-only it only makes and checks the archive.

Three easyconfig writers, by the way a code describes its build:
  generate(code, here)              dependencies read from the deps.yaml of the pinned commit,
                                    generic MakeCp template EB_TEMPLATE
  write_spec(code, here)            dependencies listed in the code data (DEPS table), easyconfig
                                    assembled line by line
  write_template(here, name, version, template, flavours, common)
                                    code-specific template in the generator, @KEY@ substitution

Environment:
  HCD_MODULES_WORK  work directory (default /scratch/users/$USER/hcd_modules); sources in <work>/sources
  HCD_GIT_ROOT      folder of the code clones (default: the folder that contains the HCD-WF clone)
  HCD_REPO_<NAME>   clone of one code (NAME upper case, non-alphanumerics as _), e.g. HCD_REPO_LHCD_MODULE
"""
import getpass
import hashlib
import os
import re
import subprocess
import sys

VERSION = '2026.10.22'
# Date label of the codes whose modules are built from a newer pinned commit than the rest: a new
# commit gets a new label, so that one module name never stands for two builds. Codes not listed
# use VERSION. Read through version_of(name) by the writers, the template generators and
# tools/build_hcd_modules.sh.
VERSION_OVERRIDES = {
    'FoPla': '2026.10.26',
    'HCD2CORE_SOURCES': '2026.10.27',
}
SITE_MODULES = '/work/imas/etc/modules/all'

LIB = os.path.dirname(os.path.abspath(__file__))
EC_ROOT = os.path.dirname(LIB)
HCD_WF = os.path.dirname(EC_ROOT)
GIT_ROOT = os.environ.get('HCD_GIT_ROOT') or os.path.dirname(HCD_WF)
WORK = os.environ.get('HCD_MODULES_WORK') or '/scratch/users/%s/hcd_modules' % (
    os.environ.get('USER') or getpass.getuser())
SOURCES_ROOT = os.path.join(WORK, 'sources')
SHA_FILE = os.path.join(EC_ROOT, 'sources.sha256')
RUN_SETUP_TEMPLATE = os.path.join(LIB, 'run_setup.sh.in')

SOURCES_ONLY = '--sources-only' in sys.argv[1:]

FLAVOURS = {
    'intel-2025b-dd4': dict(tc='2025b', dd='4.1.1', fc='ifx', gcc='14.3.0'),
    'intel-2025b-dd3': dict(tc='2025b', dd='3.42.2', fc='ifx', gcc='14.3.0'),
    'intel-2023b-dd3': dict(tc='2023b', dd='3.42.2', fc='ifort', gcc='13.2.0'),
}
# flavour -> (toolchain version, DD of IMAS-Fortran, compiler)
TC_DD_FC = {k: (v['tc'], v['dd'], v['fc']) for k, v in FLAVOURS.items()}

# yaml chosen by the code's Makefile from FC and the DD major version (checked to exist at the commit)
YAML_SUFFIX = {'intel-2025b-dd4': '_ifx.yaml', 'intel-2025b-dd3': '_ifx_dd3.yaml', 'intel-2023b-dd3': '_ifort_dd3.yaml'}


# --------------------------------------------------------------------------------------------------
# files, git, source archives

def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def write_file(path, text):
    """Writes a generated file (nothing with --sources-only); returns the sha256 of its content."""
    if not SOURCES_ONLY:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(path)
    return sha256_text(text)


def version_of(name):
    """Date label of a code: VERSION_OVERRIDES[name], else VERSION."""
    return VERSION_OVERRIDES.get(name, VERSION)


def git(repo, *args):
    return subprocess.run(['git', '-C', repo] + list(args), check=True, capture_output=True, text=True).stdout


def repo(rel, name):
    """Clone of a code: $HCD_REPO_<NAME>, else <HCD_GIT_ROOT>/<rel>."""
    var = 'HCD_REPO_' + re.sub(r'[^A-Z0-9]', '_', name.upper())
    return os.environ.get(var) or os.path.join(GIT_ROOT, rel)


def _recorded_shas():
    shas = {}
    if os.path.isfile(SHA_FILE):
        with open(SHA_FILE) as f:
            for line in f:
                if line.strip():
                    sha, rel = line.split()
                    shas[rel] = sha
    return shas


def make_archive(name, repo_dir, commit, prefix):
    """git archive --prefix=<prefix>/ of commit into <work>/sources/<letter>/<name>/<namelower>-<VERSION>.tar.gz,
    written only when missing (read-only on the clone), then checked against sources.sha256 (an archive
    without entry is recorded there)."""
    rel = os.path.join(name[0].lower(), name, '%s-%s.tar.gz' % (name.lower(), version_of(name)))
    out = os.path.join(SOURCES_ROOT, rel)
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(['git', '-C', repo_dir, 'archive', '--format=tar.gz', '--prefix=%s/' % prefix, '-o', out,
                        commit], check=True)
    sha = sha256(out)
    recorded = _recorded_shas().get(rel)
    if recorded is None:
        with open(SHA_FILE, 'a') as f:
            f.write('%s  %s\n' % (sha, rel))
        print('recorded sha256 of %s in %s' % (rel, SHA_FILE))
    elif recorded != sha:
        raise SystemExit('sha256 of %s is %s, sources.sha256 records %s (other commit or git version?)'
                         % (out, sha, recorded))
    print(out)
    return out


# --------------------------------------------------------------------------------------------------
# dependencies

_TC_RE = re.compile(r'^(?P<ver>[^-]+)-(?P<tc>intel-compilers|intel|iimkl|iimpi|iompi|GCCcore|GCC|foss|gompi)'
                    r'-(?P<tcver>[0-9][0-9.]*[a-z]?)(?P<suffix>-.*)?$')


def module_to_dep(module, tc):
    """'IMAS-Fortran/5.6.0-intel-2025b-DD-4.1.1' -> ('IMAS-Fortran', '5.6.0', '-DD-4.1.1'), toolchain intel/<tc>
    inherited; other toolchains are written explicitly."""
    name, rest = module.split('/', 1)
    m = _TC_RE.match(rest)
    if not m:
        raise SystemExit('cannot parse module %s' % module)
    suffix = m.group('suffix') or ''
    if m.group('tc') == 'intel' and m.group('tcver') == tc:
        return (name, m.group('ver'), suffix) if suffix else (name, m.group('ver'))
    return (name, m.group('ver'), suffix, (m.group('tc'), m.group('tcver')))


def check_site_module(module):
    name, rest = module.split('/', 1)
    path = os.path.join(SITE_MODULES, name, rest + '.lua')
    if not os.path.isfile(path):
        raise SystemExit('dependency %s is not a site module (%s missing)' % (module, path))


def deps_yaml(repo_dir, commit, path='deps.yaml'):
    """deps.yaml at a commit: a mapping with 'combinations' (each with its 'modules' list) and, in the
    manifests that keep Waveform-Cooker as a component, 'components' (see cooker_module)."""
    import yaml
    return yaml.safe_load(git(repo_dir, 'show', '%s:%s' % (commit, path)))


def cooker_module(manifest, combo, gcc, cooker_map=None):
    """Waveform-Cooker module of deps.yaml for a combination, with the code's replacements
    cooker_map {module prefix: replacement ({gcc} = GCCcore version)}. None when deps.yaml has no cooker."""
    comp = (manifest.get('components') or {}).get('waveform_cooker')
    if not comp:
        return None
    mod = comp['module']
    if isinstance(mod, dict):
        mod = mod[combo]
    for prefix, repl in (cooker_map or {}).items():
        if mod.startswith(prefix):
            mod = repl.format(gcc=gcc)
    return mod


def fmt_dep(d):
    """EasyBuild dependency tuple; the string 'SYSTEM' as toolchain becomes the SYSTEM constant."""
    if len(d) == 4 and d[3] == 'SYSTEM':
        return '    (%r, %r, %r, SYSTEM),' % d[:3]
    return '    ' + repr(d) + ','


# Official site modules of the three combinations (/work/imas/etc/modules/all) as EasyBuild dependency
# tuples, keyed by the module names of deps.yaml (write_spec).
SYSTEM_TC = 'SYSTEM'
DEPS = {
    'iWrap/2.0.0-intel-2025b': ('iWrap', '2.0.0'),
    'iWrap/2.0.0-intel-2023b': ('iWrap', '2.0.0'),
    'IMAS-Python/2.3.0-intel-2025b': ('IMAS-Python', '2.3.0'),
    'IMAS-Python/2.3.0-intel-2023b': ('IMAS-Python', '2.3.0'),
    'IMAS-Fortran/5.6.0-intel-2025b-DD-4.1.1': ('IMAS-Fortran', '5.6.0', '-DD-4.1.1'),
    'IMAS-Fortran/5.6.0-intel-2025b-DD-3.42.2': ('IMAS-Fortran', '5.6.0', '-DD-3.42.2'),
    'IMAS-Fortran/5.6.0-intel-2023b-DD-3.42.2': ('IMAS-Fortran', '5.6.0', '-DD-3.42.2'),
    'MUSCLE3/0.10.0-intel-2025b': ('MUSCLE3', '0.10.0'),
    'MUSCLE3/0.8.0-intel-2023b': ('MUSCLE3', '0.8.0'),
    'XMLlib/3.3.2-intel-compilers-2025.2.0': ('XMLlib', '3.3.2', '', ('intel-compilers', '2025.2.0')),
    'XMLlib/3.3.2-intel-compilers-2023.2.1': ('XMLlib', '3.3.2', '', ('intel-compilers', '2023.2.1')),
    'INTERPOS/9.2.3-iimkl-2025b': ('INTERPOS', '9.2.3', '', ('iimkl', '2025b')),
    'INTERPOS/9.2.0-iimkl-2023b': ('INTERPOS', '9.2.0', '', ('iimkl', '2023b')),
    'NAG/26-intel-compilers-2025.2.0': ('NAG', '26', '', ('intel-compilers', '2025.2.0')),
    'NAG/26-intel-compilers-2023.2.1': ('NAG', '26', '', ('intel-compilers', '2023.2.1')),
    'netCDF-Fortran/4.6.2-iimpi-2025b': ('netCDF-Fortran', '4.6.2', '', ('iimpi', '2025b')),
    'netCDF-Fortran/4.6.1-iimpi-2023b': ('netCDF-Fortran', '4.6.1', '', ('iimpi', '2023b')),
    'imkl-FFTW/2025.2.0-iimpi-2025b': ('imkl-FFTW', '2025.2.0', '', ('iimpi', '2025b')),
    'imkl-FFTW/2023.2.0-iimpi-2023b': ('imkl-FFTW', '2023.2.0', '', ('iimpi', '2023b')),
    'IDStools/2.5.0-intel-2025b': ('IDStools', '2.5.0'),
    'IDStools/2.5.0-intel-2023b': ('IDStools', '2.5.0'),
    'Fundamental-Constants/0.2.1': ('Fundamental-Constants', '0.2.1', '', SYSTEM_TC),
    'Waveform-Cooker/1.9.0-GCCcore-14.3.0': ('Waveform-Cooker', '1.9.0', '', ('GCCcore', '14.3.0')),
    'Waveform-Cooker/1.9.0-GCCcore-13.2.0': ('Waveform-Cooker', '1.9.0', '', ('GCCcore', '13.2.0')),
}

# Modules of the combinations shared by several codes (deps.yaml order)
BASE_2025B_DD4 = ['iWrap/2.0.0-intel-2025b', 'IMAS-Python/2.3.0-intel-2025b',
                  'IMAS-Fortran/5.6.0-intel-2025b-DD-4.1.1']
BASE_2025B_DD3 = ['iWrap/2.0.0-intel-2025b', 'IMAS-Python/2.3.0-intel-2025b',
                  'IMAS-Fortran/5.6.0-intel-2025b-DD-3.42.2']
BASE_2023B_DD3 = ['iWrap/2.0.0-intel-2023b', 'IMAS-Python/2.3.0-intel-2023b',
                  'IMAS-Fortran/5.6.0-intel-2023b-DD-3.42.2']
WAVEFORM_COOKER = {
    'intel-2025b-dd4': 'Waveform-Cooker/1.9.0-GCCcore-14.3.0',
    'intel-2025b-dd3': 'Waveform-Cooker/1.9.0-GCCcore-14.3.0',
    'intel-2023b-dd3': 'Waveform-Cooker/1.9.0-GCCcore-13.2.0',
}


def fmt_dep_module(mod):
    """DEPS entry of a module name, with the module name as comment."""
    dep = DEPS[mod]
    if len(dep) == 4 and dep[3] == SYSTEM_TC:
        return '    (%r, %r, %r, SYSTEM),  # %s' % (dep[0], dep[1], dep[2], mod)
    return '    %r,  # %s' % (dep, mod)


# Dependency tuples by toolchain (write_template; the toolchain of the easyconfig is implied when no
# toolchain is given).
def d_iwrap(): return ('iWrap', '2.0.0')
def d_imaspy(): return ('IMAS-Python', '2.3.0')
def d_imasf(dd): return ('IMAS-Fortran', '5.6.0', '-DD-%s' % dd)
def d_idstools(): return ('IDStools', '2.5.0')
def d_muscle3(tc): return ('MUSCLE3', '0.10.0' if tc == '2025b' else '0.8.0')
def d_xmllib(tc): return ('XMLlib', '3.3.2', '', ('intel-compilers', '2025.2.0' if tc == '2025b' else '2023.2.1'))
def d_interpos(tc): return ('INTERPOS', '9.2.3', '', ('iimkl', '2025b')) if tc == '2025b' else ('INTERPOS', '9.2.0', '', ('iimkl', '2023b'))
def d_pspline(tc): return ('PSPLINE', '2.2.0', '', ('iimpi', '2025b')) if tc == '2025b' else ('PSPLINE', '2.0.1', '', ('iimpi', '2023b'))
def d_netcdff(tc): return ('netCDF-Fortran', '4.6.2', '', ('iimpi', '2025b')) if tc == '2025b' else ('netCDF-Fortran', '4.6.1', '', ('iimpi', '2023b'))
def d_cmake(tc): return ('CMake', '3.31.8', '', ('GCCcore', '14.3.0')) if tc == '2025b' else ('CMake', '3.27.6', '', ('GCCcore', '13.2.0'))
def d_wfc190(tc): return ('Waveform-Cooker', '1.9.0', '', ('GCCcore', '14.3.0' if tc == '2025b' else '13.2.0'))
def d_iwrap_m3plugin(): return ('iWrap-plugins-MUSCLE3', '0.3.0', '', 'SYSTEM')
def d_tcsh(): return ('tcsh', '6.24.16', '', ('GCCcore', '14.3.0'))


# Build environment: the CI runs with the toolchain modules loaded but none of the compiler/MPI
# variables EasyBuild sets for the toolchain (FFLAGS -O2 -xHost etc.); they are unset.
UNSET_TOOLCHAIN_ENV = ('unset CC CXX F77 F90 FC CFLAGS CXXFLAGS FFLAGS FCFLAGS F90FLAGS F77FLAGS CPPFLAGS LDFLAGS '
                       'LIBS OPTFLAGS PRECFLAGS MPICC MPICXX MPIF77 MPIF90 MPIFC')


# --------------------------------------------------------------------------------------------------
# templates

def render(template, subst):
    text = template
    for k, v in subst.items():
        text = text.replace('@%s@' % k, v)
    left = re.findall(r'@[A-Z_]+@', text)
    assert not left, left
    return text


def _select(template, style):
    """Keeps the lines of the @@if <style> ...@@ ... @@end@@ blocks that name style."""
    out, keep = [], [True]
    for line in template.split('\n'):
        m = re.match(r'^@@if ([a-z_ ]+)@@$', line)
        if m:
            keep.append(keep[-1] and style in m.group(1).split())
        elif line == '@@end@@':
            keep.pop()
        elif keep[-1]:
            out.append(line)
    assert len(keep) == 1, 'unbalanced @@if@@ blocks'
    return '\n'.join(out)


def run_setup_text(style, subst):
    """Text of a <code>_run_setup helper from run_setup.sh.in.

    style actor_archive: kit copied without config_sdcc*.sh, actor package archived into actor.tar.gz
          actor_links:   kit copied without config_sdcc*.sh, actor packages linked from .module_actor_links
          kit_links:     kit copied as is (links to the module kept), run directory <run_dir>@RUNSUB@
    """
    with open(RUN_SETUP_TEMPLATE) as f:
        text = _select(f.read(), style)
    for k, v in subst.items():
        text = text.replace('@%s@' % k, v)
    if '@USAGE_END@' in text:
        # last line of the header comment = the line before the blank line that precedes 'set -euo pipefail'
        text = text.replace('@USAGE_END@', str(text.split('\n').index('set -euo pipefail') - 1))
    left = re.findall(r'@[A-Z_]+@', text)
    assert not left, left
    return text


def _usage(lines):
    return '\n'.join('#     %s' % ln for ln in lines)


def write_helper(path, helper, code, name, ebroot, links, rundir_doc, runsub, usage_lines):
    """kit_links helper (write_template codes); returns its sha256."""
    echo_usage = '\n'.join('echo "  %s"' % line.replace('"', '\\"').replace('$', '\\$') for line in usage_lines)
    text = run_setup_text('kit_links', {
        'HELPER': helper, 'CODE': code, 'NAME': name, 'EBROOT': ebroot, 'LINKS': links, 'RUNDIR': rundir_doc,
        'RUNSUB': runsub, 'USAGE': _usage(usage_lines), 'ECHO_USAGE': echo_usage})
    return write_file(path, text)


def _q(s):
    return repr(s)


# --------------------------------------------------------------------------------------------------
# writer 1: generate(code, here), dependencies from deps.yaml of the pinned commit

RESOLVE_STUB = r'''# ci-sdcc/resolve_deps.sh of the run kit of an H&CD actor module (sourced by ci-sdcc/st00-header.sh):
# the environment is the one of the loaded module, which sets COMBO and IMAS_VERSION and loads the
# dependency modules of its combination; nothing is resolved or loaded here and no module is purged.
if [[ -z "${COMBO:-}" || -z "${IMAS_VERSION:-}" ]]; then
    echo "resolve_deps (module run kit): COMBO or IMAS_VERSION not set: load the code's module first" >&2
    return 1 2>/dev/null || exit 1
fi
echo "resolve_deps (module run kit): environment of the loaded module, COMBO=$COMBO IMAS_VERSION=$IMAS_VERSION"
return 0 2>/dev/null || exit 0
'''

TEST_ST = r'''#!/bin/bash
# Post-install test of a @NAME@ module, called by build_hcd_modules.sh with the module loaded in a
# clean environment:
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with @CODE@_run_setup and runs the CI run case of the repository,
# @ST_SCRIPT@ (iWrap actor and MUSCLE3 actor, with its own result checks), with its work
# directory @ST_VAR@=<workdir>/@ST_SUB@; outputs and MUSCLE3 run directories stay below <workdir>.
# Appends rc and the result lines to <summary_file>; returns 0 when the script succeeds and
# printed its PASSED line.

set -uo pipefail
work=${1:?usage: test_module.sh <workdir> <summary_file>}
summary=${2:?usage: test_module.sh <workdir> <summary_file>}

say() { echo "$*" | tee -a "$summary"; }

mkdir -p "$work"
run=$work/run
@CODE@_run_setup "$run" > "$work/setup.log" 2>&1 || { say "setup: FAILED (see $work/setup.log)"; exit 1; }
say "run directory: $run"
cd "$run" || exit 1

export @ST_VAR@=$work/@ST_SUB@
log=$work/@ST_SUB@.log
t0=$(date +%s)
bash @ST_SCRIPT@ > "$log" 2>&1
rc=$?
t1=$(date +%s)
say "@ST_SCRIPT@: rc=$rc, $((t1 - t0)) s (log $log)"
grep -E "^($work|\./|/)[^ ]*: |PASSED|FAILED|iWrap vs|MUSCLE3 vs|agree" "$log" | grep -v '^+' | head -8 \
    | cut -c1-220 | sed 's/^/  /' | tee -a "$summary"
status=0
[[ $rc -eq 0 ]] && grep -q 'PASSED' "$log" || status=1
say "test status: $([[ $status -eq 0 ]] && echo PASSED || echo FAILED)"
exit $status
'''

EB_TEMPLATE = '''# @NAME@ (@TITLE@) as IMAS library, iWrap actor and MUSCLE3 actor:
# DD @DD@, toolchain intel/@TC@ (@FC@), combination @COMBO@ of deps.yaml.
# Generated by gen_easyconfigs.py (with ../_lib/hcd_ec.py); edit the generator, not this file.
easyblock = 'MakeCp'

name = '@NAME@'
version = '@VERSION@'
local_dd = '@DD@'
versionsuffix = '-DD-%s' % local_dd

# Version @VERSION@ (date label) = commit @COMMIT@ of @BRANCH_TEXT@,
# @GIT_URL@ (git describe @DESCRIBE@); source archive
# @NAMELOWER@-@VERSION@.tar.gz = git archive --prefix=@REPO_NAME@/ of that commit.
local_commit = '@COMMIT@'
local_combo = '@COMBO@'
local_fc = '@FC@'
# iWrap yaml picked by the Makefile from FC and the DD major version: @IWRAP_YAML@

homepage = '@HOMEPAGE@'
description = """@DESCRIPTION@
Version @VERSION@ is a date label: built from commit %s (git describe @DESCRIBE@) of
@BRANCH_TEXT@@SERVER_NOTE@, for DD %s (combination %s, %s): @CONTENTS@
@CODE@_run_setup <dir> makes a writable run directory from the run kit.""" % (local_commit, local_dd, local_combo, local_fc)

usage = """@USAGE@"""

toolchain = {'name': 'intel', 'version': '@TC@'}
# no -xHost/-march: the module is shared by all node types; the code's own flags are used (local_env)
toolchainopts = {'optarch': False}

sources = [
@SOURCE_ARCHIVE@
    {
        'filename': '@CODE@_run_setup.sh',
        'extract_cmd': 'cp %s .',
    },
    {
        'filename': 'resolve_deps_module.sh',
        'extract_cmd': 'cp %s .',
    },
]
checksums = [
    @ARCHIVE_SHA@,
    '@HELPER_SHA@',
    '@STUB_SHA@',
]
start_dir = '%(builddir)s/@REPO_NAME@'

@BUILDDEPS@
# combination @COMBO@ of deps.yaml (same order)@COOKER_TEXT@
dependencies = [
@DEPS@
]

# Same build environment as ci-sdcc/st00-header.sh: no toolchain compiler flags, FC of the toolchain,
# COMBO and IMAS_VERSION of the combination.
local_env = ' && '.join([
    'unset CC CXX F77 F90 CFLAGS CXXFLAGS FFLAGS FCFLAGS F90FLAGS F77FLAGS CPPFLAGS LDFLAGS LIBS OPTFLAGS PRECFLAGS',
    'export FC=%s COMBO=%s IMAS_VERSION=%s' % (local_fc, local_combo, local_dd),
])
# ACTORS_COPY_DIR=none: ci-sdcc/copy_actors.sh of the build scripts copies no actor into ~/public/PYTHON_ACTORS
local_env += ' && export ACTORS_COPY_DIR=none'

# pristine copy of the source tree (run kit), then the commands of @BUILD_SOURCE@
local_build_cmds = [
@BUILD_CMDS@
]
prebuildopts = ' && '.join([
    local_env,
    'rm -rf %(builddir)s/run_kit_src && cp -a %(start_dir)s %(builddir)s/run_kit_src',
] + local_build_cmds + [''])
# build stamp of the combination (read by run_muscle and the ci-sdcc scripts through ci-sdcc/build_stamp.sh)
build_cmd = 'bash'
buildopts = 'ci-sdcc/build_stamp.sh write .'
maxparallel = 1

files_to_copy = [
@FILES_TO_COPY@
]

local_kit = '%(installdir)s/run_kit'
postinstallcmds = [
    # run kit: tracked files of the repository at the commit, the build products and the build stamp
    'cp -a %(builddir)s/run_kit_src ' + local_kit,
@KIT_COPY@
    'install -m 0644 %(builddir)s/resolve_deps_module.sh ' + local_kit + '/ci-sdcc/resolve_deps.sh',
    # iWrap actor package %(installdir)s/@ACTOR@ (@IWRAP_SOURCE@ with ACTOR_FOLDER=%(installdir)s)
    local_env + ' && cd %(start_dir)s && export ACTOR_FOLDER=%(installdir)s && @IWRAP_CMD@',
    # MUSCLE3 executable where HCD-WF expects it ($ACTOR_FOLDER/@ACTOR@/@ACTOR@_m3.exe)
    'cp -p %(installdir)s/bin/@M3NAME@ %(installdir)s/@ACTOR@/@ACTOR@_m3.exe',
    'install -m 0755 %(builddir)s/@CODE@_run_setup.sh %(installdir)s/bin/@CODE@_run_setup',
    'find %(installdir)s -name __pycache__ -type d -prune -exec rm -rf {} +',
]

modextrapaths = {'PYTHONPATH': ''}
modextravars = {
    'IMAS_VERSION': local_dd,
    'COMBO': local_combo,
    '@EBNAME@_RUN_KIT': local_kit,
}
# stack limit of config_sdcc*.sh (ulimit -Ss unlimited)
modluafooter = 'execute{cmd="ulimit -Ss unlimited 2>/dev/null || true", modeA={"load"}}'

sanity_check_paths = {
    'files': [
@SANITY_FILES@
    ],
    'dirs': [@SANITY_DIRS@],
}

sanity_check_commands = [
@SANITY_CMDS@
]

moduleclass = 'phys'
'''


def generate(code, here):
    """code: dict describing the code (see a gen_easyconfigs.py); here: folder of the generator."""
    name, actor, cname = code['name'], code['actor'], code['code']
    version = version_of(name)
    ebname = re.sub(r'[^A-Z0-9]', 'MIN', name.upper())
    # commit checks (read-only)
    head = git(code['repo'], 'rev-parse', code['commit'] + '^{commit}').strip()
    assert head == code['commit'], (head, code['commit'])
    describe = git(code['repo'], 'describe', '--tags', '--always', code['commit']).strip()
    assert describe == code['describe'], (describe, code['describe'])
    manifest = deps_yaml(code['repo'], code['commit'])
    tracked = set(git(code['repo'], 'ls-tree', '-r', '--name-only', code['commit']).split('\n'))
    for path in code['kit_required']:
        assert path in tracked, '%s not tracked at %s' % (path, code['commit'])

    archive = make_archive(name, code['repo'], code['commit'], code['repo_name'])
    if SOURCES_ONLY:
        return
    # helper, stub and test next to the generator (EasyBuild finds them in the easyconfig folder)
    echo_lines = '\n'.join('echo "  %s"' % ln.replace('"', '\\"') for ln in code['run_lines'])
    helper = run_setup_text('actor_archive', {
        'HELPER': '%s_run_setup' % cname, 'NAME': name, 'EBROOT': 'EBROOT' + ebname, 'ACTOR': actor,
        'USAGE': _usage(code['run_lines']), 'ECHO_USAGE': echo_lines,
        'KIT_PRODUCTS': ', '.join(p for p, _ in code['kit_products'])})
    helper_path = os.path.join(here, '%s_run_setup.sh' % cname)
    helper_sha = write_file(helper_path, helper)
    stub_path = os.path.join(here, 'resolve_deps_module.sh')
    stub_sha = write_file(stub_path, RESOLVE_STUB)
    test_path = os.path.join(here, 'test_module.sh')
    if code.get('test_script'):
        write_file(test_path, code['test_script'])
    else:
        t = TEST_ST
        for k, v in {'CODE': cname, 'NAME': name, 'ST_SCRIPT': code['st_script'], 'ST_VAR': code['st_var'],
                     'ST_SUB': code['st_var'].split('_')[0].lower()}.items():
            t = t.replace('@%s@' % k, v)
        write_file(test_path, t)

    # archive_only: the easyconfig uses the local source archive (with its checksum), no git fallback
    archive_only = code.get('archive_only', False)
    if not archive_only:
        source_archive = ('    {\n        \'git_config\': {\n            \'url\': %s,\n            \'repo_name\': %s,\n'
                          '            \'commit\': local_commit,\n        },\n'
                          '        \'filename\': \'%%(namelower)s-%%(version)s.tar.gz\',\n    },'
                          % (_q(code['git_base']), _q(code['repo_name'])))
    else:
        source_archive = ('    # %s\n' % code['archive_comment'] +
                          '    {\'filename\': \'%(namelower)s-%(version)s.tar.gz\'},')

    for combo, fl in FLAVOURS.items():
        fc = fl['fc']
        yaml_file = code['yaml_prefix'] + YAML_SUFFIX[combo]
        assert yaml_file in tracked, '%s not tracked' % yaml_file
        mods = manifest['combinations'][combo]['modules']
        cooker = cooker_module(manifest, combo, fl['gcc'], code.get('cooker_map'))
        if code.get('cooker_override', {}).get(combo):
            cooker = code['cooker_override'][combo]
        all_mods = list(mods) + ([cooker] if cooker else []) + list(code.get('extra_modules', {}).get(combo, []))
        for m in all_mods:
            check_site_module(m)
        deps = [module_to_dep(m, fl['tc']) for m in all_mods]
        builddeps = [module_to_dep(m, fl['tc']) for m in code.get('build_modules', {}).get(combo, [])]
        for m in code.get('build_modules', {}).get(combo, []):
            check_site_module(m)

        def f(s):
            return s.replace('{fc}', fc)

        files_to_copy = []
        for globs, dest in code['files_to_copy']:
            files_to_copy.append('    (%s, %s),' % (repr([f(g) for g in globs]), _q(dest)))
        kit_copy = []
        for src, dest_rel in code['kit_products']:
            src, dest_rel = f(src), f(dest_rel)
            kit_copy.append("    'mkdir -p ' + local_kit + '/%s && cp -p %%(start_dir)s/%s ' + local_kit + '/%s',"
                            % (os.path.dirname(dest_rel) or '.', src, dest_rel))
        kit_copy.append("    'cp -p %(start_dir)s/.build_combo ' + local_kit + '/.build_combo',")
        m3name = os.path.basename(code['m3'])
        sanity_files = ['bin/%s' % m3name, 'bin/%s_run_setup' % cname, '%s/actor.py' % actor,
                        '%s/%s_m3.exe' % (actor, actor), 'run_kit/.build_combo', 'run_kit/%s' % code['m3'],
                        'run_kit/run_muscle', 'run_kit/coupling.ymmsl', 'run_kit/ci-sdcc/build_stamp.sh',
                        'run_kit/ci-sdcc/resolve_deps.sh'] + [f(p) for p in code['sanity_files']]
        if code.get('st_script'):
            sanity_files.append('run_kit/%s' % code['st_script'])
        sanity_dirs = ['%s/bin' % actor, '%s/lib' % actor, 'run_kit/ci-sdcc'] + code.get('sanity_dirs', [])
        cmds = ["python -c 'from %s.actor import %s as actor; print(actor)'" % (actor, actor),
                "python -c 'import ymmsl, libmuscle'"]
        if cooker:
            api = code.get('cooker_api', {}).get(combo, 'add_dynamic')
            cmds.append("python -c 'from waveform_cooker import %s'" % api)
        cmds += ["! ldd %%(installdir)s/bin/%s | grep 'not found'" % m3name,
                 "ldd %%(installdir)s/bin/%s | grep -q libmuscle" % m3name,
                 "for f in %%(installdir)s/%s/bin/*.exe; do ! ldd $f | grep 'not found' || exit 1; done" % actor,
                 'test "$IMAS_VERSION" = "$(pkg-config --modversion al-fortran | cut -d- -f1)"',
                 'bash %%(installdir)s/run_kit/ci-sdcc/build_stamp.sh check %%(installdir)s/run_kit %s' % cname,
                 '%s_run_setup --help' % cname]
        usage = '\n'.join(['module load %s/%s-intel-%s-DD-%s' % (name, version, fl['tc'], fl['dd']),
                           '%s_run_setup <dir> && cd <dir>' % cname] + code['run_lines'] +
                          list(code.get('usage_notes', [])) +
                          ['HCD-WF layout: ACTOR_FOLDER=$EBROOT%s ($ACTOR_FOLDER/%s/%s_m3.exe; actor package %s on '
                           'PYTHONPATH)' % (ebname, actor, actor, actor)])
        cooker_text = ', then Waveform-Cooker (%s)' % code['cooker_note'] if cooker else ''
        server_note = code.get('server_note', '')
        s = {
            'NAME': name, 'NAMELOWER': name.lower(), 'TITLE': code['title'], 'DD': fl['dd'], 'TC': fl['tc'],
            'FC': fc, 'COMBO': combo, 'VERSION': version, 'COMMIT': code['commit'], 'DESCRIBE': describe,
            'BRANCH_TEXT': code.get('branch_text', 'origin/feature/DD3_and_DD4'), 'SERVER_NOTE': server_note,
            'GIT_URL': code.get('repo_url') or '%s/%s.git' % (code['git_base'], code['repo_name']),
            'REPO_NAME': code['repo_name'],
            'IWRAP_YAML': yaml_file, 'HOMEPAGE': code['homepage'], 'DESCRIPTION': code['description'],
            'CONTENTS': code['contents'], 'CODE': cname, 'USAGE': usage, 'SOURCE_ARCHIVE': source_archive,
            'HELPER_SHA': helper_sha, 'STUB_SHA': stub_sha,
            # the git fallback could recreate the archive with other bytes: no checksum then
            'ARCHIVE_SHA': repr(sha256(archive)) if archive_only else 'None',
            'BUILDDEPS': ('builddependencies = [\n%s\n]\n' % '\n'.join('    %r,' % (d,) for d in builddeps)
                          if builddeps else ''),
            'COOKER_TEXT': cooker_text, 'DEPS': '\n'.join('    %r,' % (d,) for d in deps),
            'BUILD_SOURCE': code['build_source'],
            'BUILD_CMDS': '\n'.join('    %s,' % _q(f(c)) for c in code['build_cmds']),
            'FILES_TO_COPY': '\n'.join(files_to_copy), 'KIT_COPY': '\n'.join(kit_copy), 'ACTOR': actor,
            'IWRAP_SOURCE': code['iwrap_source'], 'IWRAP_CMD': f(code['iwrap_cmd']), 'M3NAME': m3name,
            'EBNAME': ebname,
            'SANITY_FILES': '\n'.join('        %s,' % _q(p) for p in sanity_files),
            'SANITY_DIRS': ', '.join(_q(d) for d in sanity_dirs),
            'SANITY_CMDS': '\n'.join('    %s,' % _q(c) for c in cmds),
        }
        text = EB_TEMPLATE
        for k, v in s.items():
            text = text.replace('@%s@' % k, v)
        left = re.findall(r'@[A-Z_]+@', text)
        assert not left, left
        write_file(os.path.join(here, '%s-%s-intel-%s-DD-%s.eb' % (name, version, fl['tc'], fl['dd'])), text)


# --------------------------------------------------------------------------------------------------
# writer 2: write_spec(code, here), dependencies listed in the code data

def _spec_helper(code, here):
    text = run_setup_text('actor_links', {
        'HELPER': code['helper'], 'NAME': code['name'], 'CODE': code['code'],
        'EBROOT': 'EBROOT' + code['name'].upper().replace('-', 'MIN'), 'USAGE': _usage(code['usage'])})
    return write_file(os.path.join(here, code['helper'] + '.sh'), text)


def easyconfig_spec(code, flavour, helper_sha):
    tc, dd, fc = TC_DD_FC[flavour]
    ddmaj = dd.split('.')[0]
    fl = code['flavours'][flavour]
    sub = dict(FC=fc, DDMAJ=ddmaj)

    def s(x):
        return x.format(**sub) if isinstance(x, str) else x

    version = version_of(code['name'])
    env_vars = [('IMAS_VERSION', dd), ('COMBO', flavour)] + list(code.get('env', []))
    kitvar = code['name'].upper().replace('-', '_') + '_RUN_KIT'
    links = [(s(path), actor) for path, actor in fl.get('links', code.get('links', []))]
    mods = fl['modules']

    L = []
    a = L.append
    a('# %s as IMAS library, iWrap actor and MUSCLE3 actor:' % code['name'])
    a('# DD %s, toolchain intel/%s (%s), combination %s of deps.yaml.' % (dd, tc, fc, flavour))
    a('# Generated by gen_easyconfigs.py (with ../_lib/hcd_ec.py); edit the generator, not this file.')
    a("easyblock = 'MakeCp'")
    a('')
    a('name = %r' % code['name'])
    a('version = %r' % version)
    a('local_dd = %r' % dd)
    a("versionsuffix = '-DD-%s' % local_dd")
    a('')
    a('# Version %s (date label) = commit %s of origin/feature/DD3_and_DD4,' % (version, code['commit']))
    a('# %s/%s.git (git describe %s); source archive' % (code['git_url'], code['git_repo'], code['describe']))
    a('# %s-%s.tar.gz = git archive --prefix=%s/ of that commit.' % (code['name'].lower(), version, code['prefix']))
    a('local_commit = %r' % code['commit'])
    a('local_combo = %r' % flavour)
    a('local_fc = %r' % fc)
    a('local_kit = %r' % '%(installdir)s/run_kit')
    a('')
    a('homepage = %r' % code['homepage'])
    a('description = """%s' % code['summary'])
    a('Version %s is a date label: built from commit %%s (git describe %s) of' % (version, code['describe']))
    a('origin/feature/DD3_and_DD4, for DD %%s: %s' % code['provides'])
    a('%s <dir> makes a writable run directory from the run kit (run_kit).""" %% (local_commit, local_dd)'
      % code['helper'])
    a('')
    a("toolchain = {'name': 'intel', 'version': %r}" % tc)
    if code.get('toolchainopts'):
        if code.get('toolchainopts_comment'):
            a('# %s' % code['toolchainopts_comment'])
        a('toolchainopts = %r' % code['toolchainopts'])
    a('')
    a('sources = [')
    a('    {')
    a("        'git_config': {")
    a("            'url': %r," % code['git_url'])
    a("            'repo_name': %r," % code['git_repo'])
    a("            'commit': local_commit,")
    a('        },')
    a("        'filename': '%(namelower)s-%(version)s.tar.gz',")
    a('    },')
    a('    {')
    a("        'filename': %r," % (code['helper'] + '.sh'))
    a("        'extract_cmd': 'cp %s .',")
    a('    },')
    a(']')
    a('checksums = [')
    a('    None,')
    a('    %r,' % helper_sha)
    a(']')
    a("start_dir = '%%(builddir)s/%s'" % code['prefix'])
    a('')
    a('# combination %s of deps.yaml (same order)%s' % (
        flavour, ', then the Waveform-Cooker component' if code.get('waveform_cooker') else ''))
    a('dependencies = [')
    for m in mods:
        L.append(fmt_dep_module(m))
    if code.get('waveform_cooker'):
        L.append(fmt_dep_module(WAVEFORM_COOKER[flavour]))
    a(']')
    a('')
    a('# Build environment of ci-sdcc/st00-header.sh: no toolchain compiler flags, FC of the toolchain,')
    a('# COMBO and IMAS_VERSION of the combination%s.' % (
        ', and the variables of the env files' if code.get('env') else ''))
    exports = ' '.join(['FC=%s' % fc] + ['%s=%s' % (k, v) for k, v in env_vars])
    a('local_env = %r' % (
        'unset CC CXX F77 F90 CFLAGS CXXFLAGS FFLAGS FCFLAGS F90FLAGS F77FLAGS CPPFLAGS LDFLAGS LIBS '
        'OPTFLAGS PRECFLAGS && export ' + exports))
    a('# ACTORS_COPY_DIR=none: ci-sdcc/copy_actors.sh of the build scripts copies no actor into ~/public/PYTHON_ACTORS')
    a("local_env += ' && export ACTORS_COPY_DIR=none'")
    a('')
    a('# ci-sdcc/st01-build-code.sh: %s' % code['build_note'])
    pre = ' && '.join(['local_env_PLACEHOLDER'] + [s(c) for c in code['prebuild']]) + ' &&'
    assert "'" not in pre, 'single quote in a build command'
    a('prebuildopts = %s' % repr(pre).replace("'local_env_PLACEHOLDER", "local_env + '"))
    a("build_cmd = 'make'")
    a('build_cmd_targets = %r' % s(code['target']))
    a('buildopts = %r' % s(code['buildopts']))
    a('maxparallel = 1')
    a('')
    a('files_to_copy = [')
    for files, dest in code['files']:
        a('    (%r, %r),' % ([s(x) for x in files], dest))
    a(']')
    a('')
    a('postinstallcmds = [')
    a('    # iWrap actor package %%(installdir)s/%s (ci-sdcc/st02-build-actor.sh with' % code['actor'])
    a('    # ACTOR_FOLDER=%(installdir)s; the Makefile picks the yaml from FC and IMAS_VERSION)')
    a("    local_env + ' && cd %%(start_dir)s && %s'," % s(code['actor_cmd']))
    a('    # MUSCLE3 executable inside the actor package ($ACTOR_FOLDER/<actor>/ layout of HCD-WF)')
    a("    'cp -p %%(installdir)s/bin/%s %%(installdir)s/%s/%s'," % (
        os.path.basename(s(code['m3'])), code['actor'], os.path.basename(s(code['m3']))))
    a('    # run kit: the build tree (tracked files of the pinned commit and the build products at their')
    a('    # repository paths, without object files), the build stamp of the combination and the links')
    a('    # to the actor package that the run scripts expect (made by %s)' % code['helper'])
    excl = ' '.join("--exclude=%s" % e for e in ["'*.o'", "'__pycache__'", './ci-deps'] + code.get('kit_exclude', []))
    a("    'mkdir -p ' + local_kit + %r + local_kit," % (' && cd %(start_dir)s && tar ' + excl + ' -cf - . | tar -xf - -C '))
    a("    local_env + ' && cd ' + local_kit + ' && bash ci-sdcc/build_stamp.sh write .',")
    link_lines = ''.join('%s %s\\\\n' % (p, act) for p, act in links)
    a("    \"printf '%s' > \" + local_kit + '/.module_actor_links'," % link_lines)
    a("    'install -m 0755 %%(builddir)s/%s.sh %%(installdir)s/bin/%s'," % (code['helper'], code['helper']))
    for extra in code.get('postinstall_extra', []):
        a('    %r,' % s(extra))
    a("    'find %(installdir)s -name __pycache__ -type d -prune -exec rm -rf {} +',")
    a(']')
    a('')
    a("modextrapaths = {'PYTHONPATH': ''}")
    a('modextravars = {')
    for k, v in env_vars:
        a('    %r: %r,' % (k, v))
    a("    %r: local_kit," % kitvar)
    a('}')
    a('# stack limit of the config_sdcc*.sh files')
    a("modluafooter = 'execute{cmd=\"ulimit -Ss unlimited 2>/dev/null || true\", modeA={\"load\"}}'")
    a('')
    m3base = os.path.basename(s(code['m3']))
    act = code['actor']
    files = (['bin/%s' % m3base, 'bin/%s' % code['helper']]
             + [s(x) for x in code['sanity_files']]
             + ['%s/actor.py' % act, '%s/bin/%s_main.exe' % (act, act), '%s/lib/lib%s.so' % (act, act),
                '%s/%s' % (act, m3base),
                'run_kit/.build_combo', 'run_kit/.module_actor_links', 'run_kit/%s' % s(code['m3']),
                'run_kit/run_muscle', 'run_kit/coupling.ymmsl', 'run_kit/deps.yaml',
                'run_kit/ci-sdcc/build_stamp.sh', 'run_kit/ci-sdcc/st00-header.sh',
                'run_kit/ci-sdcc/resolve_deps.sh']
             + ['run_kit/%s' % s(x) for x in code['kit_files']])
    a('sanity_check_paths = {')
    a("    'files': [")
    for f in files:
        a('        %r,' % f)
    a('    ],')
    a("    'dirs': %r," % (['%s/input' % act, 'run_kit/input'] + [s(x) for x in code.get('sanity_dirs', [])]))
    a('}')
    a('')
    a('sanity_check_commands = [')
    a('    %r,' % ("python -c 'from %s.actor import %s as a; print(a)'" % (act, act)))
    a('    %r,' % ("python -c '%s'" % code.get('py_check', 'import imas, ymmsl, libmuscle')))
    a('    %r,' % ("! ldd %%(installdir)s/bin/%s | grep 'not found'" % m3base))
    a('    %r,' % ("! ldd %%(installdir)s/%s/bin/%s_main.exe | grep 'not found'" % (act, act)))
    a('    %r,' % ("ldd %%(installdir)s/bin/%s | grep -q libmuscle" % m3base))
    a("    'test \"$IMAS_VERSION\" = \"$(pkg-config --modversion al-fortran | cut -d- -f1)\"',")
    a('    %r,' % ('bash %%(installdir)s/run_kit/ci-sdcc/build_stamp.sh check %%(installdir)s/run_kit %s'
                   % code['stamp_code']))
    a('    %r,' % ('%s --help' % code['helper']))
    a(']')
    a('')
    a("moduleclass = 'phys'")
    return '\n'.join(L) + '\n'


def write_spec(code, here):
    make_archive(code['name'], code['repo'], code['commit'], code['prefix'])
    if SOURCES_ONLY:
        return
    helper_sha = _spec_helper(code, here)
    for flavour, (tc, dd, fc) in TC_DD_FC.items():
        text = easyconfig_spec(code, flavour, helper_sha)
        write_file(os.path.join(here, '%s-%s-intel-%s-DD-%s.eb' % (code['name'], version_of(code['name']), tc, dd)), text)


# --------------------------------------------------------------------------------------------------
# writer 3: write_template(...), code-specific template with @KEY@ values

def write_template(here, name, version, template, flavours, common):
    """Write <name>-<version>-intel-<tc>-DD-<dd>.eb for each flavour.

    flavours: key -> dict with 'builddeps', 'deps' (lists of tuples) and further @KEY@ values;
    common: @KEY@ values shared by all flavours.
    """
    if SOURCES_ONLY:
        return
    for key, fl in flavours.items():
        tc, dd, fc = TC_DD_FC[key]
        subst = dict(common)
        subst.update({'TC': tc, 'DD': dd, 'FC': fc, 'COMBO': key, 'VERSION': version})
        subst.update({k: v for k, v in fl.items() if k not in ('builddeps', 'deps')})
        subst['BUILDDEPS'] = '\n'.join(fmt_dep(d) for d in fl.get('builddeps', []))
        subst['DEPS'] = '\n'.join(fmt_dep(d) for d in fl['deps'])
        text = render(template, subst)
        write_file(os.path.join(here, '%s-%s-intel-%s-DD-%s.eb' % (name, version, tc, dd)), text)
