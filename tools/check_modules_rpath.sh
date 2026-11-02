#!/bin/bash
# Checks the shared libraries of installed EasyBuild modules of the user module tree. For every install
# directory <prefix>/software/<CODE>/<version>-<toolchain...> of the selected version it lists the ELF files
# (executables and *.so*, outside run_kit/, no *.py) with
#   RPATH     an RPATH/RUNPATH entry pointing into a build tree (*/eb_build/*, */eb_tmp/*, /tmp/*);
#             $ORIGIN entries are fine
#   NOTFOUND  a library that ldd cannot resolve with the RPATH plus the LD_LIBRARY_PATH set by the module
#             itself (module purge; module use <site> <prefix>/modules/all; module load <CODE>/<dir>)
#   LDPATH    (information only) a library that resolves only through that module LD_LIBRARY_PATH,
#             i.e. ldd without LD_LIBRARY_PATH reports it "not found"
# and prints one line per install directory:
#   SUMMARY <CODE> <version-toolchain> build-tree-rpath=N notfound=N module-ldpath=N
# Without a loadable module (no .lua) NOTFOUND is evaluated without LD_LIBRARY_PATH and a NOTE line says so.
#
# Usage: check_modules_rpath.sh [--prefix DIR] [--version V] [--no-module-env] [CODE | CODE/<dir> ...]
#   --prefix DIR      EasyBuild tree (default ${EB_PREFIX:-/work/projects/pds/stack})
#   --version V       version label to check (default ${CHECK_VERSION:-}; empty: the newest label of each
#                     code, the part of the directory name before the toolchain, by version sort, so that
#                     2026.11.02.1 > 2026.11.02 > 2026.10.22); all toolchains/flavours of that label are checked
#   --no-module-env   evaluate NOTFOUND without LD_LIBRARY_PATH for every install (no module load)
#   CODE              code folder under <prefix>/software (default: all of them)
#   CODE/<dir>        one install directory, i.e. one module name (e.g. GRAY/2026.11.02.1-intel-2025b-DD-4.1.1)
# Environment: HCD_SITE_MODULES  site module path used with module load (default /work/imas/etc/modules/all)
# Exit status: 0 if every SUMMARY has build-tree-rpath=0 and notfound=0, 1 otherwise (also when a CODE or
# CODE/<dir> has no install directory: MISSING line), 2 on usage errors.
# Read-only; fine on the login node (about 15 minutes for the whole tree, seconds to a minute per code).
set -uo pipefail

PREFIX=${EB_PREFIX:-/work/projects/pds/stack}
VERSION=${CHECK_VERSION:-}
SITE_MODULES=${HCD_SITE_MODULES:-/work/imas/etc/modules/all}
modenv=1
targets=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --prefix|--version)
            [[ $# -ge 2 ]] || { echo "$1 needs a value" >&2; exit 2; }
            [[ $1 == --prefix ]] && PREFIX=$2 || VERSION=$2
            shift ;;
        --no-module-env) modenv=0 ;;
        -h|--help) sed -n '2,/^set /p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "unknown option $1" >&2; exit 2 ;;
        *) targets+=("$1") ;;
    esac
    shift
done
SW=${PREFIX%/}/software
[[ -d $SW ]] || { echo "no software directory: $SW" >&2; exit 2; }
if [[ ${#targets[@]} -eq 0 ]]; then
    mapfile -t targets < <(ls "$SW")
fi
if [[ $modenv == 1 ]]; then
    type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh 2>/dev/null
    type module >/dev/null 2>&1 || { echo "NOTE: no module command; NOTFOUND evaluated without LD_LIBRARY_PATH"; modenv=0; }
fi

# version label of an install directory name: the part before the toolchain (first '-' followed by a letter)
label() { sed 's/-[A-Za-z].*//'; }
# newest version label of a code
pick_version() { ls "$1" 2>/dev/null | label | sort -uV | tail -1; }
# LD_LIBRARY_PATH set by loading module <CODE>/<dir> in a clean module environment; fails if it cannot load
module_ldpath() {
    (
        module purge >/dev/null 2>&1
        module use "$SITE_MODULES" >/dev/null 2>&1
        module use "${PREFIX%/}/modules/all" >/dev/null 2>&1
        module load "$1" >/dev/null 2>&1 || exit 1
        printf '%s' "${LD_LIBRARY_PATH:-}"
    )
}
# libraries reported "not found" by ldd for file $1 with LD_LIBRARY_PATH=$2 (unset if empty)
missing() {
    if [[ -n $2 ]]; then env LD_LIBRARY_PATH="$2" ldd "$1" 2>/dev/null
    else env -u LD_LIBRARY_PATH ldd "$1" 2>/dev/null; fi | awk '/not found/ {print $1}' | sort -u | tr '\n' ' '
}

check_dir() {
    local c=$1 d=$2 name=${2##*/} bad=0 nf=0 lp=0 f e rp m0 m1 ldp=""
    if [[ $modenv == 1 ]]; then
        if ! ldp=$(module_ldpath "$c/$name"); then
            echo "NOTE $c $name: module $c/$name cannot be loaded; NOTFOUND evaluated without LD_LIBRARY_PATH"
            ldp=""
        fi
    fi
    while IFS= read -r f; do
        file -b "$f" | grep -q '^ELF' || continue
        rp=$(readelf -d "$f" 2>/dev/null | grep -E 'RPATH|RUNPATH' | sed 's/.*\[//;s/\]//')
        for e in ${rp//:/ }; do
            case "$e" in
                '$ORIGIN'*) ;;
                */eb_build/*|*/eb_tmp/*|/tmp/*) echo "RPATH $c $name ${f#"$d"/} -> $e"; bad=$((bad+1)) ;;
            esac
        done
        m0=$(missing "$f" "")
        [[ -n $m0 ]] || continue
        m1=$m0
        [[ -n $ldp ]] && m1=$(missing "$f" "$ldp")
        if [[ -n $m1 ]]; then
            echo "NOTFOUND $c $name ${f#"$d"/}: $m1"; nf=$((nf+1))
        else
            echo "LDPATH $c $name ${f#"$d"/}: $m0"; lp=$((lp+1))
        fi
    done < <(find "$d" -type f \( -perm -u+x -o -name '*.so*' \) -not -path '*/run_kit/*' -not -name '*.py' 2>/dev/null)
    echo "SUMMARY $c $name build-tree-rpath=$bad notfound=$nf module-ldpath=$lp"
    [[ $bad -eq 0 && $nf -eq 0 ]]
}

status=0 n=0
for t in "${targets[@]}"; do
    c=${t%%/*}
    [[ -d $SW/$c ]] || { echo "MISSING $c: no directory $SW/$c"; status=1; continue; }
    dirs=()
    if [[ $t == */* ]]; then
        [[ -d $SW/$t ]] && dirs=("$SW/$t")
    else
        v=$VERSION; [[ -n $v ]] || v=$(pick_version "$SW/$c")
        for d in "$SW/$c/$v"-*; do
            [[ -d $d && $(basename "$d" | label) == "$v" ]] && dirs+=("$d")
        done
    fi
    if [[ ${#dirs[@]} -eq 0 ]]; then
        echo "MISSING $t: no install directory under $SW"; status=1; continue
    fi
    for d in "${dirs[@]}"; do
        check_dir "$c" "$d" || status=1
        n=$((n+1))
    done
done
echo "checked $n install directories under $SW: $([[ $status == 0 ]] && echo OK || echo FAILED)"
exit $status
