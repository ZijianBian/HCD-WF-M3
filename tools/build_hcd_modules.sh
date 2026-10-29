#!/bin/bash
# Builds the H&CD actor modules with EasyBuild into the user module tree /work/projects/pds/stack
# (software in /work/projects/pds/stack/software, modules in /work/projects/pds/stack/modules/all),
# one module per code and flavour, and tests each new module in a clean environment. Installs are
# readable by all and writable by the owner only (umask 022). Single place of the method:
# build_modules.sbatch only calls this script. Documentation: tools/README_modules.md.
#
#   build_hcd_modules.sh [options] <code|all> [<flavour|all>]
#
#   flavours: intel-2025b-dd4 (DD 4.1.1), intel-2025b-dd3 (DD 3.42.2), intel-2023b-dd3 (DD 3.42.2);
#             default all
#   --submit        one Slurm job per (code, flavour): sbatch build_modules.sbatch ... <code> <flavour>
#   --dry-run       eb --dry-run and eb --extended-dry-run only (no build; EasyBuild prefix, sources and
#                   ebfiles_repo in the work directory, the real install path is only printed); fine on
#                   the login node
#   --make-sources  (re)creates the missing source archives in <work>/sources with git archive from the
#                   local clones (gen_easyconfigs.py --sources-only) and checks them against
#                   easyconfigs/sources.sha256; no build; fine on the login node
#   --no-test       skip the post-install test
#   --rebuild       eb --rebuild (replaces an existing module of the same name)
#   --list          print the code -> easyconfig table and exit
#
# Without --submit, --dry-run or --make-sources the build runs in the current shell, which must be a
# Slurm allocation (sbatch job, or an interactive srun/salloc shell on a compute node, partition sun).
#
# Examples:
#   build_hcd_modules.sh --make-sources all
#   build_hcd_modules.sh --dry-run TORBEAM intel-2023b-dd3
#   build_hcd_modules.sh --submit TORBEAM            # three jobs, one per flavour
#   build_hcd_modules.sh --submit all all            # every code of the table, every flavour
#
# Using the modules:
#   module use /work/projects/pds/stack/modules/all
#   module load TORBEAM/2026.10.22-intel-2025b-DD-4.1.1    # or ...-intel-2025b-DD-3.42.2,
#                                                          # ...-intel-2023b-DD-3.42.2
#
# Environment:
#   HCD_MODULES_WORK  work directory: eb_build, eb_tmp, logs, tests, sources, dryrun
#                     (default /scratch/users/$USER/hcd_modules); nothing is written into the repository
#   HCD_EC_DIR        easyconfig folder (default <repository>/easyconfigs)
#   EB_PREFIX         EasyBuild install tree (default /work/projects/pds/stack)
#   HCD_GIT_ROOT, HCD_REPO_<NAME>  clones used by --make-sources (see easyconfigs/_lib/hcd_ec.py)

set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_DIR=$(dirname "$HERE")
EC_ROOT=${HCD_EC_DIR:-$REPO_DIR/easyconfigs}
BASE=${HCD_MODULES_WORK:-/scratch/users/${USER:-$(id -un)}/hcd_modules}
PREFIX=${EB_PREFIX:-/work/projects/pds/stack}
SITE_MODULES=/work/imas/etc/modules/all
EB_MODULE=EasyBuild/5.4.1
export HCD_MODULES_WORK=$BASE

# date label of the modules: VERSION of the generator library (per-code labels below)
VERSION=$(sed -n "s/^VERSION = '\([^']*\)'.*/\1/p" "$EC_ROOT/_lib/hcd_ec.py")
[[ -n "$VERSION" ]] || { echo "no VERSION in $EC_ROOT/_lib/hcd_ec.py" >&2; exit 2; }

# Codes; the easyconfig of a pair is <EC_ROOT>/<code>/<code>-<VERSION>-intel-<toolchain>-DD-<dd>.eb.
# The code folder may hold test_module.sh <workdir> <summary> (post-install test, module loaded).
CODE_ORDER=(TORBEAM GRAY GRAYSCALE TORAY GENRAY RELAX FPSIM CYRANO TOMCAT LION PION TORIC StixReDist FoPla NEMO NBISIM FUSREAC SPECE HCD2CORE_SOURCES HCD_MERGERS HCD2CORE_PROFILES LHCD-MODULE CHEASE RABBIT RISK SPOT ASCOT)
declare -A CODE_EC=()
for c in "${CODE_ORDER[@]}"; do CODE_EC[$c]=$c/$c-$VERSION; done
# per-code date labels (VERSION_OVERRIDES of the generator library)
overrides=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import hcd_ec
for c, v in sorted(hcd_ec.VERSION_OVERRIDES.items()): print(c, v)' "$EC_ROOT/_lib") \
    || { echo "cannot read VERSION_OVERRIDES of $EC_ROOT/_lib/hcd_ec.py" >&2; exit 2; }
while read -r c v; do
    [[ -n "$c" ]] || continue
    [[ -n "${CODE_EC[$c]:-}" ]] || { echo "VERSION_OVERRIDES: unknown code $c" >&2; exit 2; }
    CODE_EC[$c]=$c/$c-$v
done <<< "$overrides"
# Extra sbatch options per code (override the #SBATCH lines of build_modules.sbatch): MPI tests
# (up to 4 MPI processes plus the workflow / manager processes) and the long ASCOT build
declare -A CODE_SBATCH=(
    [RISK]="--cpus-per-task=6 --mem=32G"
    [SPOT]="--cpus-per-task=6 --mem=32G"
    [ASCOT]="--cpus-per-task=6 --mem=48G --time=04:00:00"
)

FLAVOURS=(intel-2025b-dd4 intel-2025b-dd3 intel-2023b-dd3)
declare -A FLAVOUR_TC=([intel-2025b-dd4]=2025b [intel-2025b-dd3]=2025b [intel-2023b-dd3]=2023b)
declare -A FLAVOUR_DD=([intel-2025b-dd4]=4.1.1 [intel-2025b-dd3]=3.42.2 [intel-2023b-dd3]=3.42.2)

usage() { sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed -e '/^$/d' -e 's/^# \{0,1\}//'; }

submit=0 dry=0 notest=0 rebuild=0 mksrc=0
args=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --submit)       submit=1 ;;
        --dry-run)      dry=1 ;;
        --make-sources) mksrc=1 ;;
        --no-test)      notest=1 ;;
        --rebuild)      rebuild=1 ;;
        --list)
            for c in "${CODE_ORDER[@]}"; do
                for f in "${FLAVOURS[@]}"; do
                    echo "$c $f $EC_ROOT/${CODE_EC[$c]}-intel-${FLAVOUR_TC[$f]}-DD-${FLAVOUR_DD[$f]}.eb"
                done
            done
            exit 0 ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "unknown option $1" >&2; usage >&2; exit 2 ;;
        *) args+=("$1") ;;
    esac
    shift
done
[[ ${#args[@]} -ge 1 && ${#args[@]} -le 2 ]] || { usage >&2; exit 2; }

if [[ ${args[0]} == all ]]; then
    codes=("${CODE_ORDER[@]}")
else
    [[ -n "${CODE_EC[${args[0]}]:-}" ]] || { echo "unknown code ${args[0]} (known: ${CODE_ORDER[*]})" >&2; exit 2; }
    codes=("${args[0]}")
fi
if [[ ${args[1]:-all} == all ]]; then
    flavours=("${FLAVOURS[@]}")
else
    [[ -n "${FLAVOUR_TC[${args[1]}]:-}" ]] || { echo "unknown flavour ${args[1]} (known: ${FLAVOURS[*]})" >&2; exit 2; }
    flavours=("${args[1]}")
fi

# --- source archives: git archive of the pinned commits, checked against sources.sha256 ------------
if [[ $mksrc == 1 ]]; then
    mkdir -p "$BASE/logs"
    status=0
    for c in "${codes[@]}"; do
        log=$BASE/logs/make_sources_$c.log
        PYTHONDONTWRITEBYTECODE=1 python3 "$EC_ROOT/$c/gen_easyconfigs.py" --sources-only > "$log" 2>&1
        rc=$?
        echo "$c: sources rc=$rc (log $log)"
        [[ $rc -eq 0 ]] || status=1
    done
    ( cd "$BASE/sources" && sha256sum --quiet -c "$EC_ROOT/sources.sha256" --ignore-missing ) || status=1
    exit $status
fi

# --- submission: one job per pair, each job runs this script on one pair --------------------------
if [[ $submit == 1 ]]; then
    opts=()
    [[ $notest == 1 ]] && opts+=(--no-test)
    [[ $rebuild == 1 ]] && opts+=(--rebuild)
    mkdir -p "$BASE/logs"
    for c in "${codes[@]}"; do
        for f in "${flavours[@]}"; do
            # shellcheck disable=SC2086
            sbatch -J "hcd_${c}_${f}" -o "$BASE/logs/%x_%j.log" ${CODE_SBATCH[$c]:-} "$HERE/build_modules.sbatch" \
                "$HERE/build_hcd_modules.sh" HCD_MODULES_WORK="$BASE" HCD_EC_DIR="$EC_ROOT" EB_PREFIX="$PREFIX" \
                "${opts[@]}" "$c" "$f" || exit 1
        done
    done
    exit 0
fi

if [[ $dry == 0 && -z "${SLURM_JOB_ID:-}" ]]; then
    echo "not in a Slurm allocation: use --submit, an interactive srun shell on a compute node, or --dry-run" >&2
    exit 2
fi

type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh

# --- one (code, flavour) pair ---------------------------------------------------------------------
build_one() {
    local code=$1 flavour=$2
    local ec=$EC_ROOT/${CODE_EC[$code]}-intel-${FLAVOUR_TC[$flavour]}-DD-${FLAVOUR_DD[$flavour]}.eb
    local ecname modname job summary eblog rc t0 t1
    ecname=$(basename "$ec" .eb)
    modname=$code/${ecname#"$code"-}
    job=${SLURM_JOB_ID:-login}
    mkdir -p "$BASE/logs"
    summary=$BASE/logs/summary_${code}_${flavour}_${job}$([[ $dry == 1 ]] && echo _dryrun).txt
    : > "$summary"
    say() { echo "$*" | tee -a "$summary"; }
    say "code=$code flavour=$flavour host=$(hostname) job=$job"
    say "easyconfig=$ec"
    say "module=$modname prefix=$PREFIX"
    [[ -f "$ec" ]] || { say "ERROR: easyconfig missing"; return 1; }
    eblog=$BASE/logs/eb_${code}_${flavour}_${job}$([[ $dry == 1 ]] && echo _dryrun).log

    (
        module purge
        module use "$SITE_MODULES"
        module load "$EB_MODULE" || { echo "ERROR: module load $EB_MODULE failed"; exit 1; }
        # Same settings as the existing installs of the tree (prefix = installpath = PREFIX,
        # repositorypath PREFIX/ebfiles_repo, umask 022); the tree directories carry the setgid bit.
        # Build and temporary directories stay in the work directory.
        export EASYBUILD_INSTALLPATH=$PREFIX
        if [[ $dry == 1 ]]; then
            export EASYBUILD_PREFIX=$BASE/dryrun
            export EASYBUILD_REPOSITORYPATH=$BASE/dryrun/ebfiles_repo
            export EASYBUILD_SOURCEPATH=$BASE/sources:$PREFIX/sources
            export EASYBUILD_LOCKS_DIR=$BASE/dryrun/locks
        else
            export EASYBUILD_PREFIX=$PREFIX
            export EASYBUILD_REPOSITORYPATH=$PREFIX/ebfiles_repo
            export EASYBUILD_SOURCEPATH=$PREFIX/sources:$BASE/sources
        fi
        # per-process directories outside Slurm (job=login, e.g. dry runs): concurrent runs must not
        # remove each other's build and temporary directories; cleanup below removes only these
        ebjob=$job
        [[ -z "${SLURM_JOB_ID:-}" ]] && ebjob=${job}_$$
        export EASYBUILD_BUILDPATH=$BASE/eb_build/$ebjob
        export EASYBUILD_TMPDIR=$BASE/eb_tmp/$ebjob
        export EASYBUILD_UMASK=022
        export EASYBUILD_SET_GID_BIT=1
        unset EASYBUILD_GROUP_WRITABLE_INSTALLDIR
        export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
        umask 022
        mkdir -p "$EASYBUILD_BUILDPATH" "$EASYBUILD_TMPDIR"
        # No --robot: every dependency must already exist as a module (official site modules); eb
        # stops with "Missing modules for dependencies" otherwise and never rebuilds an official module.
        if [[ $dry == 1 ]]; then
            eb "$ec" --dry-run && eb "$ec" --extended-dry-run
        else
            eb "$ec" $([[ $rebuild == 1 ]] && echo --rebuild)
        fi
        rc=$?
        rm -rf "$EASYBUILD_BUILDPATH" "$EASYBUILD_TMPDIR"
        exit $rc
    ) > "$eblog" 2>&1
    rc=$?
    say "eb$([[ $dry == 1 ]] && echo ' dry run'): rc=$rc, log $eblog"
    if [[ $rc -ne 0 ]]; then
        grep -m5 -E 'ERROR|FAILED' "$eblog" | cut -c1-300 | tee -a "$summary"
        return $rc
    fi
    if [[ $dry == 1 || $notest == 1 || ! -f "$EC_ROOT/$code/test_module.sh" ]]; then
        say "test: skipped"
        return 0
    fi

    # post-install test: new module loaded in a clean environment, run from a scratch copy
    local work=$BASE/tests/${code}_${flavour}_${job}
    rm -rf "$work"
    mkdir -p "$work"
    local test_rc=0
    local -a slurm_env=()
    local kv
    while IFS= read -r -d '' kv; do [[ $kv == SLURM_* ]] && slurm_env+=("$kv"); done < <(env -0)
    env -i HOME="$HOME" USER="$USER" LOGNAME="${LOGNAME:-$USER}" SHELL=/bin/bash TERM=dumb \
        PATH=/usr/local/bin:/usr/bin:/bin "${slurm_env[@]}" SLURM_EXPORT_ENV=ALL \
        timeout 30m bash -l -c '
            type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
            module purge
            module use '"$SITE_MODULES"'
            module use '"$PREFIX"'/modules/all
            module load '"$modname"' || exit 1
            export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
            echo "loaded: $(module -t list 2>&1 | tr "\n" " ")"
            bash '"$EC_ROOT/$code"'/test_module.sh '"$work"' '"$summary"'
        ' > "$work/test.log" 2>&1 || test_rc=$?
    say "test: rc=$test_rc, log $work/test.log"
    return $test_rc
}

status=0
for c in "${codes[@]}"; do
    for f in "${flavours[@]}"; do
        build_one "$c" "$f" || status=1
    done
done
exit $status
