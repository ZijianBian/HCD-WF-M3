#!/bin/bash
# Source from the repository root with COMBO set to a combination of deps.yaml, e.g.
#     COMBO=intel-2025b-dd4 bash ci-sdcc/st03-regression.sh
# ci-sdcc/resolve_deps.sh loads the combination's modules and writes ci-deps/env.sh;
# CI mode unless DEPS_MODE=interactive. In CI mode MODULES, when set, replaces the modules
# of the families it names (accepted while CI plans still pass the module list as a plan variable).
source "$(dirname "${BASH_SOURCE[0]}")/resolve_deps.sh" || return 1
shopt -s expand_aliases

# FC is the compiler of the loaded toolchain (ifort for intel-2023b, ifx for intel-2025b);
# a preset FC must name the same compiler. The actor Makefiles select their iWrap yaml from it.
if command -v ifort >/dev/null 2>&1; then
    _st00_fc=ifort
elif command -v ifx >/dev/null 2>&1; then
    _st00_fc=ifx
elif command -v gfortran >/dev/null 2>&1; then
    _st00_fc=gfortran
else
    echo "ERROR: No supported Fortran compiler (ifort/ifx/gfortran) found in loaded modules." >&2
    return 1
fi
if [[ -n "${FC:-}" && "$FC" != "$_st00_fc" ]]; then
    echo "st00: preset FC=$FC differs from the compiler of the loaded modules ($_st00_fc) - unset it or load the matching modules" >&2
    unset _st00_fc
    return 1
fi
export FC=$_st00_fc
unset _st00_fc

# IMAS_VERSION (DD version of the workflow output and of the reference directory dd-<IMAS_VERSION>)
# comes from the loaded IMAS-Fortran module (pkg-config al-fortran reports <DD version>-<AL version>,
# e.g. 4.1.1-5.6.0); a preset IMAS_VERSION must match it.
_st00_imas=$(pkg-config --modversion al-fortran 2>/dev/null | cut -d- -f1)
if [[ -z "$_st00_imas" ]]; then
    echo "ERROR: IMAS_VERSION cannot be derived from 'pkg-config --modversion al-fortran'. Is an IMAS-Fortran module in the module list?" >&2
    unset _st00_imas
    return 1
fi
if [[ -n "${IMAS_VERSION:-}" && "$IMAS_VERSION" != "$_st00_imas" ]]; then
    echo "st00: preset IMAS_VERSION=$IMAS_VERSION differs from the loaded IMAS-Fortran $_st00_imas - unset it or load the matching modules" >&2
    unset _st00_imas
    return 1
fi
export IMAS_VERSION=$_st00_imas
unset _st00_imas

echo "> Loaded modules"
module list 2>&1
echo "> Using COMBO=$COMBO, FC=$FC, IMAS_VERSION=$IMAS_VERSION"
