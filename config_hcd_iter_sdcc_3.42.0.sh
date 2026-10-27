#!/usr/bin/env bash
# Legacy DD3 stack used by #12 (DD 3.42.2); retain the historical filename.
# Use config_hcd_iter_sdcc.sh for the DD 4.1.0 MUSCLE3 runtime.

_hcd_setup_legacy_environment() {
    local source_root venv_directory dependency
    source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || return
    if ! type module >/dev/null 2>&1; then
        echo "ERROR: The SDCC module command is unavailable." >&2
        return 1
    fi
    if [[ -n "${VIRTUAL_ENV:-}" ]] && declare -F deactivate >/dev/null; then
        deactivate
    fi

    # Match Prasad's DD3 regression environment; do not load old AL actors.
    module purge || return
    for dependency in \
        IMAS-Python/2.3.0-intel-2023b \
        iWrap/2.0.0-intel-2023b \
        XMLlib/3.3.2-intel-compilers-2023.2.1 \
        lxml/4.9.3-GCCcore-13.2.0 \
        INTERPOS/9.2.0-iimkl-2023b \
        NAG/26-intel-compilers-2023.2.1 \
        Waveform-Cooker/1.8.1-GCCcore-13.2.0 \
        Fundamental-Constants/0.2.1 \
        IMAS-Fortran/5.6.0-intel-2023b-DD-3.42.2; do
        module load "${dependency}" || return
    done
    # Tkinter provides the GUI without changing the regression's SciPy stack.
    module load Tkinter/3.11.5-GCCcore-13.2.0 || return
    export IMAS_VERSION=3.42.2
    export PYTHONPATH="${source_root}${ACTOR_FOLDER:+:${ACTOR_FOLDER}}${PYTHONPATH:+:${PYTHONPATH}}"
    ulimit -Ss unlimited 2>/dev/null || true

    # Use #12's separate environment, leaving the historical AL venv untouched.
    venv_directory="${HCDWF_VENV_DIR:-${source_root}/virtualenvdir}"
    if [[ ! -d "${venv_directory}" ]]; then
        python3 -m venv "${venv_directory}" --system-site-packages || return
    fi
    source "${venv_directory}/bin/activate" || return
    if [[ "${HCDWF_SKIP_PIP_INSTALL:-1}" != "1" ]]; then
        python3 -m pip install -e "${source_root}" || return
    fi
    python3 -c 'import imas, lxml.etree, tkinter, waveform_cooker; assert imas.IDSFactory().dd_version == "3.42.2"' || return
    echo "HCD-WF Legacy environment ready: IMAS-Python, DD 3.42.2."
    echo "Use iWrap actors built for this DD3 environment."
}

if _hcd_setup_legacy_environment; then
    unset -f _hcd_setup_legacy_environment
else
    unset -f _hcd_setup_legacy_environment
    echo "ERROR: HCD-WF Legacy environment setup failed." >&2
    return 1 2>/dev/null || exit 1
fi
