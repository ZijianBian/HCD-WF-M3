#!/usr/bin/env bash
# Source this file for the legacy DD 3.42.0 iWrap actor installation on SDCC.
# Use config_hcd_iter_sdcc.sh for the DD 4.1.0 MUSCLE3 runtime.

_hcd_setup_legacy_environment() {
    local source_root venv_directory actor_module
    source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || return
    if ! type module >/dev/null 2>&1; then
        echo "ERROR: The SDCC module command is unavailable." >&2
        return 1
    fi
    module purge || return
    module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0 || return
    # Keep compiled Python extensions on the IMAS stack's Python 3.11 ABI.
    module load Tkinter/3.11.5-GCCcore-13.2.0 || return
    module load matplotlib/3.8.2-iimkl-2023b || return
    module load lxml/4.9.3-GCCcore-13.2.0 || return
    module load Waveform-Cooker/1.6.0-GCCcore-13.2.0 || return
    if [[ -n "${ACTOR_FOLDER:-}" ]]; then
        export PYTHONPATH="${ACTOR_FOLDER}${PYTHONPATH:+:${PYTHONPATH}}"
    else
        for actor_module in \
            HCD_MERGERS/1.0.0 HCD2CORE_SOURCES/1.2.0 HCD2CORE_PROFILES/1.1.0 \
            GRAYSCALE/1.1.0 GRAY/1.0.0 TORBEAM/3.8.0 TORAY/1.0.0 GENRAY/10.11.3 \
            CYRANO/1.0.0 FoPla/2.1.0 StixReDist/2.1.0 TOMCAT/1.0.0 \
            NEMO/2.2.0 NBISIM/1.3.0 RISK/2.2.0 SPOT/2.4.0 \
            RELAX/1.0.0 SMART/0.1.0 FPSIM/1.0.0; do
            module load "${actor_module}-intel-2023b-DD-3.42.0" || return
        done
    fi
    export PYTHONPATH="${source_root}${PYTHONPATH:+:${PYTHONPATH}}"
    export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1
    ulimit -Ss unlimited 2>/dev/null || true
    venv_directory="${HCDWF_VENV_DIR:-${source_root}/devenv_3.42.0}"
    if [[ ! -d "${venv_directory}" ]]; then
        python3 -m venv "${venv_directory}" --system-site-packages || return
    fi
    source "${venv_directory}/bin/activate" || return
    if [[ "${HCDWF_SKIP_PIP_INSTALL:-1}" != "1" ]]; then
        python3 -m pip install -e "${source_root}" || return
    fi
    python3 -c 'import imas, lxml.etree, tkinter, matplotlib, waveform_cooker' || return
    echo "HCD-WF legacy environment ready: DD 3.42.0."
}

if _hcd_setup_legacy_environment; then
    unset -f _hcd_setup_legacy_environment
else
    unset -f _hcd_setup_legacy_environment
    echo "ERROR: HCD-WF legacy environment setup failed." >&2
    return 1 2>/dev/null || exit 1
fi
