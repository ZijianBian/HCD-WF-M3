#!/usr/bin/env bash
# Source this file to select the SDCC DD 4.1.0 runtime.
# Shell options are deliberately left unchanged for interactive callers.

_hcd_setup_environment() {
    local source_root venv_directory
    source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || return
    if ! type module >/dev/null 2>&1; then
        echo "ERROR: The SDCC module command is unavailable." >&2
        return 1
    fi

    # The actors must share the DD release and MUSCLE3 wire protocol. Rabbit's
    # separate process selects the matching GCC stack in scripts/run_rabbit_m3.sh.
    module purge || return
    module load IMAS-Python/2.3.0-intel-2023b || return
    module load IMAS-Fortran/5.5.0-intel-2023b-DD-4.1.0 || return
    module load MUSCLE3/0.8.0-intel-2023b || return
    module load XMLlib/3.2.0-intel-compilers-2023.2.1 || return
    module load INTERPOS/9.2.0-iimkl-2023b || return
    module load Tkinter/3.11.5-GCCcore-13.2.0 || return
    module load Waveform-Cooker/1.6.0-GCCcore-13.2.0 || return

    export HCD_SANDBOX="${HCD_SANDBOX:-${source_root}}"
    export ACTOR_FOLDER="${ACTOR_FOLDER:-${source_root}/PYTHON_ACTORS}"
    export PYTHONPATH="${source_root}:${ACTOR_FOLDER}${PYTHONPATH:+:${PYTHONPATH}}"
    if [[ -n "${HCDWF_WAVEFORM_COOKER:-}" ]]; then
        export PYTHONPATH="${HCDWF_WAVEFORM_COOKER}:${PYTHONPATH}"
        export EBROOTWAVEFORMMINCOOKER="${HCDWF_WAVEFORM_COOKER}"
    fi
    if [[ -n "${HCDWF_IWRAP_ROOT:-}" ]]; then
        export PATH="${HCDWF_IWRAP_ROOT}/bin:${PATH}"
        export PYTHONPATH="${HCDWF_IWRAP_ROOT}/python:${PYTHONPATH}"
    fi
    export IMAS_AL_DISABLE_VALIDATE=1
    export PYTHONUNBUFFERED=1
    ulimit -Ss unlimited 2>/dev/null || true

    # Inherit the module-provided NumPy and IMAS ABI. Keep environment setup
    # network-free unless the caller explicitly opts into dependency installation.
    venv_directory="${HCDWF_VENV_DIR:-${source_root}/devenv_dd410}"
    if [[ ! -d "${venv_directory}" ]]; then
        python3 -m venv "${venv_directory}" --system-site-packages || return
    fi
    source "${venv_directory}/bin/activate" || return
    if [[ "${HCDWF_SKIP_PIP_INSTALL:-1}" != "1" ]]; then
        python3 -m pip install -e "${source_root}" || return
    fi
    python3 -c 'import imas, libmuscle, yaml' || return
    echo "HCD-WF environment ready: DD 4.1.0, MUSCLE3 0.8.0."
    echo "Actor installation: ${ACTOR_FOLDER}"
}

if _hcd_setup_environment; then
    unset -f _hcd_setup_environment
else
    unset -f _hcd_setup_environment
    echo "ERROR: HCD-WF environment setup failed." >&2
    return 1 2>/dev/null || exit 1
fi
