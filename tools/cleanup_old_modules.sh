#!/bin/bash
# Removes an older set of H&CD EasyBuild modules (<CODE>/<old-version>-intel-<tc>-DD-<dd><old-suffix>)
# from the user module tree once its replacement <CODE>/<new-version>-intel-<tc>-DD-<dd> (no suffix,
# the naming of build_hcd_modules.sh) is installed and the latest real (non-dry-run) build job of that
# code and flavour reported "eb: rc=0" and "test: rc=0" in its summary file. Documentation:
# tools/README_modules.md, section "Replacing an older set of modules".
#
# Usage: cleanup_old_modules.sh [--dry-run] [--yes] [--old-version V] [--old-suffix S]
#                               [--new-version V] [--prefix DIR] [--work DIR]
#   default / --dry-run : print what would be done, delete nothing (--dry-run always wins over --yes)
#   --yes               : actually delete (old install dir + old .lua, then empty <CODE> dirs)
#   --old-version V     : version label of the set to remove (default 2026.10.21)
#   --old-suffix S      : suffix of the set to remove, may be empty (default -pds)
#   --new-version V     : version label of the replacement (default: VERSION of
#                         easyconfigs/_lib/hcd_ec.py, as build_hcd_modules.sh)
#   --prefix DIR        : EasyBuild tree (default ${EB_PREFIX:-/work/projects/pds/stack})
#   --work DIR          : build work directory holding logs/summary_*.txt
#                         (default ${HCD_MODULES_WORK:-/scratch/users/$USER/hcd_modules})
# <prefix>/ebfiles_repo is never touched.
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_DIR=$(dirname "$HERE")
EC_ROOT=${HCD_EC_DIR:-$REPO_DIR/easyconfigs}

OLD_DATE=2026.10.21
OLD_SUFFIX=-pds
NEW_DATE=""
STACK=${EB_PREFIX:-/work/projects/pds/stack}
WORK=${HCD_MODULES_WORK:-/scratch/users/${USER:-$(id -un)}/hcd_modules}

doit=0 dry=0
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) dry=1 ;;
        --yes) doit=1 ;;
        --old-version|--old-suffix|--new-version|--prefix|--work)
            [[ $# -ge 2 ]] || { echo "$1 needs a value" >&2; exit 2; }
            case $1 in
                --old-version) OLD_DATE=$2 ;;
                --old-suffix) OLD_SUFFIX=$2 ;;
                --new-version) NEW_DATE=$2 ;;
                --prefix) STACK=$2 ;;
                --work) WORK=$2 ;;
            esac
            shift ;;
        -h|--help) sed -n 2,19p "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done
# --dry-run always wins over --yes
[[ $dry == 1 ]] && doit=0

if [[ -z $NEW_DATE ]]; then
    NEW_DATE=$(sed -n "s/^VERSION = '\([^']*\)'.*/\1/p" "$EC_ROOT/_lib/hcd_ec.py")
    [[ -n $NEW_DATE ]] || { echo "no VERSION in $EC_ROOT/_lib/hcd_ec.py; give --new-version" >&2; exit 2; }
fi

# Input checks: restricted character sets, so that only '.' and '+' need escaping in the regexes.
[[ $OLD_DATE =~ ^[A-Za-z0-9_.]+$ ]] || { echo "invalid --old-version: $OLD_DATE" >&2; exit 2; }
[[ $NEW_DATE =~ ^[A-Za-z0-9_.]+$ ]] || { echo "invalid --new-version: $NEW_DATE" >&2; exit 2; }
[[ -z $OLD_SUFFIX || $OLD_SUFFIX =~ ^-[A-Za-z0-9_.+-]+$ ]] \
    || { echo "invalid --old-suffix (empty or '-...'): $OLD_SUFFIX" >&2; exit 2; }
[[ $OLD_DATE == "$NEW_DATE" && -z $OLD_SUFFIX ]] \
    && { echo "old set ($OLD_DATE, no suffix) is the new set; refusing" >&2; exit 2; }
[[ $STACK == /* && $STACK != *//* && $STACK =~ ^[A-Za-z0-9_./+-]+$ && $STACK != / ]] \
    || { echo "invalid --prefix (absolute plain path expected): $STACK" >&2; exit 2; }
STACK=${STACK%/}
[[ -d $STACK ]] || { echo "prefix not found: $STACK" >&2; exit 2; }

SW=$STACK/software
MOD=$STACK/modules/all
LOGS=$WORK/logs

re_esc() { local s=${1//./\\.}; printf '%s' "${s//+/\\+}"; }
OLD_RE=$(re_esc "$OLD_DATE")
SUF_RE=$(re_esc "$OLD_SUFFIX")
SW_RE=$(re_esc "$SW")
MOD_RE=$(re_esc "$MOD")

echo "old set: <CODE>/$OLD_DATE-intel-<tc>-DD-<dd>$OLD_SUFFIX -> new set: <CODE>/$NEW_DATE-intel-<tc>-DD-<dd>"
echo "prefix: $STACK  summaries: $LOGS"
[[ $doit == 1 ]] && echo "MODE: delete (--yes)" || echo "MODE: dry run (nothing deleted; use --yes to delete)"

# Guarded rm: only exact old-module paths are accepted.
safe_rm() {
    local p=$1 kind=$2
    case $kind in
        dir)
            [[ $p =~ ^$SW_RE/[A-Za-z0-9_.+-]+/$OLD_RE-intel-[A-Za-z0-9_.+-]*$SUF_RE$ && -d $p && ! -L $p ]] \
                || { echo "  REFUSED (pattern/type check failed): $p"; return 1; } ;;
        lua)
            [[ $p =~ ^$MOD_RE/[A-Za-z0-9_.+-]+/$OLD_RE-intel-[A-Za-z0-9_.+-]*$SUF_RE\.lua$ && -f $p && ! -L $p ]] \
                || { echo "  REFUSED (pattern/type check failed): $p"; return 1; } ;;
        *) return 1 ;;
    esac
    if [[ $doit == 1 ]]; then
        if [[ $kind == dir ]]; then rm -rf -- "$p"; else rm -f -- "$p"; fi || { echo "  rm FAILED: $p"; return 1; }
        echo "  removed $p"
    else
        echo "  would remove $p"
    fi
}

# Remove $SW/<CODE> or $MOD/<CODE> only if empty.
rm_if_empty() {
    local d=$1
    [[ $d =~ ^($SW_RE|$MOD_RE)/[A-Za-z0-9_.+-]+$ && -d $d && ! -L $d ]] || return 0
    if [[ $doit == 1 ]]; then
        rmdir -- "$d" 2>/dev/null && echo "  removed empty dir $d"
    elif [[ -z $(ls -A -- "$d" 2>/dev/null) ]]; then
        echo "  would remove empty dir $d"
    fi
    return 0
}

removed=0 kept=0
declare -A why=() touched_codes=()

shopt -s nullglob
for lua in "$MOD"/*/"$OLD_DATE"-intel-*"$OLD_SUFFIX".lua; do
    code=$(basename "$(dirname "$lua")")
    old=$(basename "$lua" .lua)                  # <old-version>-intel-<tc>-DD-<dd><old-suffix>
    if [[ ! $old =~ ^$OLD_RE-intel-(20[0-9]{2}[ab])-DD-([0-9.]+)$SUF_RE$ ]]; then
        echo "KEEP $code/$old: unexpected name"; why["unexpected name"]=$(( ${why["unexpected name"]:-0} + 1 )); kept=$((kept+1)); continue
    fi
    tc=${BASH_REMATCH[1]} dd=${BASH_REMATCH[2]}
    flavour=intel-$tc-dd${dd%%.*}
    new=$NEW_DATE-intel-$tc-DD-$dd
    if [[ $new == "$old" ]]; then
        echo "KEEP $code/$old: same name as the new module"; why["same as new"]=$(( ${why["same as new"]:-0} + 1 )); kept=$((kept+1)); continue
    fi
    echo "$code/$old -> $code/$new ($flavour)"

    reason=""
    if [[ ! -f $MOD/$code/$new.lua ]]; then
        reason="new .lua missing"
    elif [[ ! -d $SW/$code/$new ]]; then
        reason="new install dir missing"
    else
        latest=""
        for s in $(ls -t "$LOGS"/summary_"${code}"_"${flavour}"_*.txt 2>/dev/null); do
            [[ $s == *_dryrun.txt ]] && continue
            latest=$s; break
        done
        if [[ -z $latest ]]; then
            reason="no non-dry-run summary"
        elif ! grep -qE '^eb: rc=0(,|$)' "$latest"; then
            reason="latest build not eb rc=0 ($(basename "$latest"))"
        elif ! grep -qE '^test: rc=0(,|$)' "$latest"; then
            reason="latest build not test rc=0 ($(basename "$latest"))"
        fi
    fi

    if [[ -n $reason ]]; then
        echo "  KEEP: $reason"
        key=${reason%% (*}
        why[$key]=$(( ${why[$key]:-0} + 1 ))
        kept=$((kept+1))
        continue
    fi

    ok=1
    if [[ -e $SW/$code/$old ]]; then safe_rm "$SW/$code/$old" dir || ok=0
    else echo "  (old install dir already absent: $SW/$code/$old)"; fi
    [[ $ok == 1 ]] && { safe_rm "$lua" lua || ok=0; }
    if [[ $ok == 1 ]]; then
        removed=$((removed+1)); touched_codes[$code]=1
    else
        kept=$((kept+1)); why["rm refused/failed"]=$(( ${why["rm refused/failed"]:-0} + 1 ))
    fi
done

for code in "${!touched_codes[@]}"; do
    rm_if_empty "$SW/$code"
    rm_if_empty "$MOD/$code"
done

echo "----"
echo "$([[ $doit == 1 ]] && echo removed || echo 'would remove'): $removed"
echo "kept: $kept"
for k in "${!why[@]}"; do echo "  $k: ${why[$k]}"; done
