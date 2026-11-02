#!/bin/bash
# Sets up the environment of one target combination from the manifest deps.yaml.
# Source it (bash), do not execute it:
#     export COMBO=intel-2025b-dd4; source ci-sdcc/resolve_deps.sh
# It is sourced by ci-sdcc/st00-header.sh (CI steps) and, through st00, by the config_sdcc*.sh env files.
#
# Every dependency is a module, official (site tree) or built into the user tree (module_paths).
#
# Variables
#   COMBO          both         combination of deps.yaml (CI: set in the task; interactive: by the env file)
#   DEPS_MODE      both         'interactive' in the env files; unset or any other value = CI mode
#   MODULES        CI only      transition: space-separated module list passed by old plans, used in place
#                               of `modules`; when COMBO is unset it is derived from the IMAS-Fortran module
#                               of MODULES (IMAS-Fortran/<ver>-intel-<YYYYt>-DD-<major>.<minor> ->
#                               intel-<YYYYt>-dd<major>)
#   <src_override> interactive  variable of interactive.src_overrides, e.g. WAVEFORM_COOKER_SRC=<source tree>
#   DEPS_FILE      both         manifest (default: the nearest deps.yaml in ci-sdcc/ or a directory above it)
#   CI_DEPS_DIR    both         directory of env.sh (default ./ci-deps)
#   SITE_MODULEPATH both        site module tree (default /work/imas/etc/modules/all)
#   DEPS_OVERLAY   interactive  EasyBuild prefix of the user tree (default /work/projects/pds/stack)
#   DEPS_NO_BUILD  interactive  set to never build a missing module
#
# Resolution
#  1. deps.yaml is read with the system Python (/usr/bin/python3) and PyYAML, before any module is loaded.
#  2. module purge, `module use` of the site tree, `module use -a` of each module_paths entry (appended:
#     a module name that exists in the site tree is taken from there).
#  3. Module list = combinations.<COMBO>.modules. CI mode: when MODULES is set it replaces the modules of
#     the families it names; the families of `modules` it does not name are kept, after it.
#     Interactive mode: for each interactive.src_overrides variable that is set, the modules of family
#     `replaces` leave the list, the source tree goes on PYTHONPATH and <root_env>=<tree> is exported.
#  4. Each module is loaded in order. A missing module is an error in CI mode (CI never builds). In
#     interactive mode a missing module listed in interactive.easyconfigs is built with
#     `eb <recipe> --robot` into DEPS_OVERLAY (EasyBuild from interactive.easybuild_module when eb is not
#     available, clean module environment, 2 build processes, umask 022) when DEPS_OVERLAY is writable
#     and DEPS_NO_BUILD is unset, then loaded; otherwise it is an error.
#  5. Interactive mode: combinations.<COMBO>.interactive_modules are loaded (a missing one is a warning).
#  6. $CI_DEPS_DIR/env.sh records the module paths, the loaded modules and the source overrides; it is
#     sourced, then every command of `checks` runs (a failure is an error).
# Returns non-zero (without exiting the calling shell) on any failure.

_rd_main() {
    local combo=${COMBO:-}
    local mode=ci
    [[ "${DEPS_MODE:-}" == interactive ]] && mode=interactive
    local here
    here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P) || return 1
    local deps_file=${DEPS_FILE:-}
    if [[ -z "$deps_file" ]]; then
        # nearest deps.yaml in ci-sdcc/ or in a directory above it
        local up=$here
        while [[ "$up" != / && ! -f "$up/deps.yaml" ]]; do up=$(dirname "$up"); done
        deps_file=$up/deps.yaml
    fi
    if [[ ! -r "$deps_file" ]]; then
        echo "resolve_deps: ERROR: manifest $deps_file not readable" >&2
        return 1
    fi
    deps_file=$(cd "$(dirname "$deps_file")" && pwd -P)/$(basename "$deps_file")
    local sys_python=/usr/bin/python3
    [[ -x "$sys_python" ]] || sys_python=python3

    local modules_override=""
    if [[ "$mode" == ci ]]; then
        modules_override=${MODULES:-}
    elif [[ -n "${MODULES:-}" ]]; then
        echo "resolve_deps: MODULES is read in CI mode only, ignored"
    fi
    if [[ -z "$combo" && -n "$modules_override" ]]; then
        local word derived=""
        for word in $modules_override; do
            if [[ "$word" =~ ^IMAS-Fortran/[^/]*-intel-([0-9]{4}[a-z])-DD-([0-9]+)\.[0-9]+ ]]; then
                derived="intel-${BASH_REMATCH[1]}-dd${BASH_REMATCH[2]}"
                break
            fi
        done
        if [[ -n "$derived" ]]; then
            combo=$derived
            export COMBO=$combo
            echo "resolve_deps: COMBO derived from MODULES: $combo"
        fi
    fi
    if [[ -z "$combo" ]]; then
        echo "resolve_deps: ERROR: set COMBO to a combination of $deps_file (e.g. intel-2025b-dd4)" >&2
        return 1
    fi
    local deps_dir=${CI_DEPS_DIR:-$PWD/ci-deps}
    local overlay=${DEPS_OVERLAY:-/work/projects/pds/stack}
    local site_path=${SITE_MODULEPATH:-/work/imas/etc/modules/all}

    mkdir -p "$deps_dir" || return 1
    deps_dir=$(cd "$deps_dir" && pwd -P) || return 1
    local records="$deps_dir/deps_$combo.tsv"
    local env_file="$deps_dir/env.sh"
    # env.sh of a previous run must not enter the environment set up below
    rm -f "$env_file"

    echo "resolve_deps: manifest $deps_file, combination $combo, $mode mode"
    "$sys_python" -s -E - "$deps_file" "$combo" > "$records" <<'EOF' || return 1
import sys
import yaml

path, combo = sys.argv[1], sys.argv[2]
data = yaml.safe_load(open(path)) or {}
combos = data.get("combinations") or {}
if combo not in combos:
    raise SystemExit("resolve_deps: ERROR: combination %r not in %s (known: %s)" % (combo, path, ", ".join(combos)))
inter = data.get("interactive") or {}

def out(kind, *values):
    for v in values:
        v = "" if v is None else str(v)
        if "\x1f" in v or "\n" in v:
            raise SystemExit("resolve_deps: ERROR: control character or newline in %r of %s" % (v, path))
    print(kind, *values, sep="\x1f")

for p in data.get("module_paths") or []:
    out("P", p)
for m in combos[combo].get("modules") or []:
    out("M", m)
for m in combos[combo].get("interactive_modules") or []:
    out("I", m)
for c in data.get("checks") or []:
    out("K", c)
if inter.get("easybuild_module"):
    out("E", inter["easybuild_module"])
for mod, recipe in (inter.get("easyconfigs") or {}).items():
    out("X", mod, recipe)
for var, o in (inter.get("src_overrides") or {}).items():
    out("S", var, o.get("replaces"), o.get("root_env"))
EOF

    local kind a b c
    local -a mpaths=() mods=() imods=() checks=() ecs=() srcs=()
    local eb_module=""
    while IFS=$'\x1f' read -r kind a b c; do
        case "$kind" in
            P) mpaths+=("$a") ;;
            M) mods+=("$a") ;;
            I) imods+=("$a") ;;
            K) checks+=("$a") ;;
            E) eb_module=$a ;;
            X) ecs+=("$a"$'\x1f'"$b") ;;
            S) srcs+=("$a"$'\x1f'"$b"$'\x1f'"$c") ;;
        esac
    done < "$records"

    if ! type module >/dev/null 2>&1; then
        source /etc/profile.d/modules.sh || return 1
    fi
    module purge || return 1
    module use "$site_path" || return 1
    local p trees=$site_path
    local -a used_paths=()
    for p in "${mpaths[@]}"; do
        if [[ -d "$p" ]]; then
            module use -a "$p" || return 1
            used_paths+=("$p")
            trees="$trees $p"
            echo "resolve_deps: module path $p (after the site tree)"
        else
            echo "resolve_deps: module path $p absent, skipped"
        fi
    done

    # module list
    local -a load=() override=()
    local m o fam
    if [[ -n "$modules_override" ]]; then
        read -r -a override <<< "$modules_override"
        load=("${override[@]}")
        for m in "${mods[@]}"; do
            fam=${m%%/*}
            local named=""
            for o in "${override[@]}"; do [[ "${o%%/*}" == "$fam" ]] && named=1; done
            [[ -z "$named" ]] && load+=("$m")
        done
        echo "resolve_deps: module list from MODULES (transition), completed with the families of combination $combo it does not name"
    else
        load=("${mods[@]}")
    fi
    if [[ ${#load[@]} -eq 0 ]]; then
        echo "resolve_deps: ERROR: empty module list for $combo" >&2
        return 1
    fi

    # source overrides (interactive mode)
    local -a env_override=()
    local entry var replaces root_env tree
    if [[ "$mode" == interactive ]]; then
        for entry in "${srcs[@]}"; do
            IFS=$'\x1f' read -r var replaces root_env <<< "$entry"
            [[ -n "${!var:-}" ]] || continue
            tree=$(cd "${!var}" 2>/dev/null && pwd -P) || {
                echo "resolve_deps: ERROR: $var=${!var} is not a directory" >&2; return 1; }
            local -a kept=()
            local dropped=""
            for m in "${load[@]}"; do
                if [[ -n "$replaces" && "${m%%/*}" == "$replaces" ]]; then dropped="$dropped $m"; else kept+=("$m"); fi
            done
            load=("${kept[@]}")
            local rev=""
            if git -C "$tree" rev-parse --git-dir >/dev/null 2>&1; then
                rev=" ($(git -C "$tree" log -1 --format='%h %cd' --date=short) $(git -C "$tree" rev-parse --abbrev-ref HEAD))"
            fi
            echo "resolve_deps: $var: source tree $tree$rev replaces${dropped:- no module of family $replaces}"
            env_override+=("# $var: source tree $tree$rev in place of${dropped:- family $replaces}")
            env_override+=("export PYTHONPATH=\"$tree\${PYTHONPATH:+:\$PYTHONPATH}\"")
            [[ -n "$root_env" ]] && env_override+=("export $root_env=\"$tree\"")
        done
    fi

    # load the modules
    local -a loaded=()
    local recipe built_path=""
    for m in "${load[@]}"; do
        if module is-avail "$m" >/dev/null 2>&1; then
            module load "$m" || { echo "resolve_deps: ERROR: module $m found but does not load" >&2; return 1; }
            loaded+=("$m")
            continue
        fi
        recipe=""
        if [[ "$mode" == interactive ]]; then
            for entry in "${ecs[@]}"; do
                [[ "${entry%%$'\x1f'*}" == "$m" ]] && recipe=${entry#*$'\x1f'}
            done
        fi
        if [[ -z "$recipe" ]]; then
            echo "resolve_deps: ERROR: module $m not found (searched: $trees)" >&2
            return 1
        fi
        if [[ -n "${DEPS_NO_BUILD:-}" || ! -d "$overlay" || ! -w "$overlay" || ! -f "$recipe" ]]; then
            echo "resolve_deps: ERROR: module $m not found (searched: $trees); not built from $recipe" \
                 "(DEPS_NO_BUILD set, $overlay not writable or recipe missing)" >&2
            return 1
        fi
        echo "resolve_deps: building $m from $recipe into $overlay (log $deps_dir/eb_${m//\//_}.log)"
        if ! ( module purge || exit 1
               if ! command -v eb >/dev/null 2>&1 && [[ -n "$eb_module" ]]; then module load "$eb_module" || exit 1; fi
               command -v eb >/dev/null 2>&1 || { echo "eb not available"; exit 1; }
               export EASYBUILD_PREFIX=${EASYBUILD_PREFIX:-$overlay} EASYBUILD_PARALLEL=${EASYBUILD_PARALLEL:-2} \
                      EASYBUILD_UMASK=${EASYBUILD_UMASK:-022}
               eb "$recipe" --robot ) > "$deps_dir/eb_${m//\//_}.log" 2>&1; then
            echo "resolve_deps: ERROR: eb failed for $m (see $deps_dir/eb_${m//\//_}.log)" >&2
            return 1
        fi
        if [[ " ${used_paths[*]} " != *" $overlay/modules/all "* ]]; then
            module use -a "$overlay/modules/all" || return 1
            used_paths+=("$overlay/modules/all")
            built_path=$overlay/modules/all
        fi
        module load "$m" || { echo "resolve_deps: ERROR: module $m built but does not load" >&2; return 1; }
        loaded+=("$m")
    done
    if [[ "$mode" == interactive ]]; then
        for m in "${imods[@]}"; do
            if module is-avail "$m" >/dev/null 2>&1 && module load "$m"; then
                loaded+=("$m")
            else
                echo "resolve_deps: WARNING: interactive module $m not available, skipped" >&2
            fi
        done
    fi

    {
        echo "# Written by ci-sdcc/resolve_deps.sh: combination $combo, $mode mode, manifest $deps_file"
        echo "module use $site_path"
        for p in "${used_paths[@]}"; do echo "module use -a $p"; done
        for m in "${loaded[@]}"; do echo "module load $m"; done
        for entry in "${env_override[@]}"; do echo "$entry"; done
    } > "$env_file"
    [[ -n "$built_path" ]] && echo "resolve_deps: user tree $built_path added for a module built in this run"

    echo "resolve_deps: sourcing $env_file"
    source "$env_file" || { echo "resolve_deps: ERROR: sourcing $env_file failed" >&2; return 1; }
    local i=0
    for c in "${checks[@]}"; do
        i=$((i + 1))
        echo "resolve_deps: check $i"
        eval "$c" || { echo "resolve_deps: ERROR: check $i of $deps_file failed" >&2; return 1; }
    done
    return 0
}

if _rd_main; then
    unset -f _rd_main
    return 0 2>/dev/null || exit 0
fi
unset -f _rd_main
return 1 2>/dev/null || exit 1
