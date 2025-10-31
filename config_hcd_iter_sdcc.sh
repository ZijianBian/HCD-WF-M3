#!/usr/bin/env bash
module purge >& /dev/null
set -uo pipefail

usage() {
    cat <<'EOF'
Usage: config_hcd_iter_sdcc.sh [dd_version]

Arguments:
  dd_version    Optional. Data Dictionary release to load (default: 3.42.0).
                Supported values: 3.42.0.

Environment variables:
  ACTOR_FOLDER  Directory containing actors compiled locally with
                actor_install.py. When set, module loading is skipped and
                the folder is prepended to PYTHONPATH.

Examples:
  config_hcd_iter_sdcc.sh
  config_hcd_iter_sdcc.sh 4.0.0
  ACTOR_FOLDER=/path/to/local/actors config_hcd_iter_sdcc.sh

EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

DD_VERSION="${1:-3.42.0}"
ACTOR_FOLDER_ENV="${ACTOR_FOLDER:-}"
VENV_DIR="devenv"


echo "[setup_dev_env] Using DD data version: ${DD_VERSION}"
if [[ -n "${ACTOR_FOLDER_ENV}" ]]; then
    echo "[setup_dev_env] Using local actors from: ${ACTOR_FOLDER_ENV}"
fi

ulimit -Ss unlimited
export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

if [[ -n "${ACTOR_FOLDER_ENV}" ]]; then
    export PYTHONPATH="${ACTOR_FOLDER_ENV}:${PYTHONPATH}"
    echo "[setup_dev_env] Skipping module loading; actors expected in ${ACTOR_FOLDER_ENV}"
elif command -v module >/dev/null 2>&1; then
    load_modules() {
        local mod
        for mod in "$@"; do
            module load "$mod"
        done
    }

    echo "[setup_dev_env] Loading core modules"
    load_modules Python Tkinter matplotlib lxml Waveform-Cooker

    CORE_MODULE=""
    MANDATORY_MODULES=()
    EC_MODULES=()
    IC_MODULES=()
    NBI_MODULES=()
    OTHER_MODULES=()

    case "${DD_VERSION}" in
        3.42.0)
            CORE_MODULE="IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0"
            MANDATORY_MODULES=(
                "HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0"
                "HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0"
                "HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0"
            )
            EC_MODULES=(
                "GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0"
                "GRAY/1.0.0-intel-2023b-DD-3.42.0"
                "TORBEAM/3.8.0-intel-2023b-DD-3.42.0"
                "TORAY/1.0.0-intel-2023b-DD-3.42.0"
                "GENRAY/10.11.3-intel-2023b-DD-3.42.0"
            )
            IC_MODULES=(
                "CYRANO/1.0.0-intel-2023b-DD-3.42.0"
                "FoPla/2.1.0-intel-2023b-DD-3.42.0"
                "StixReDist/2.1.0-intel-2023b-DD-3.42.0"
                "TOMCAT/1.0.0-intel-2023b-DD-3.42.0"
            )
            NBI_MODULES=(
                "NEMO/2.2.0-intel-2023b-DD-3.42.0"
                "NBISIM/1.3.0-intel-2023b-DD-3.42.0"
                "RISK/2.2.0-intel-2023b-DD-3.42.0"
                "SPOT/2.4.0-intel-2023b-DD-3.42.0"
            )
            OTHER_MODULES=(
                "RELAX/1.0.0-intel-2023b-DD-3.42.0"
                "SMART/0.1.0-intel-2023b-DD-3.42.0"
                "FPSIM/1.0.0-intel-2023b-DD-3.42.0"
            )
            ;;
        # Add case for 4.0.0
    esac

    echo "[setup_dev_env] Loading IMAS access layer"
    load_modules "${CORE_MODULE}"

    echo "[setup_dev_env] Loading mandatory actor modules"
    load_modules "${MANDATORY_MODULES[@]}"

    echo "[setup_dev_env] Loading EC heating actors"
    load_modules "${EC_MODULES[@]}"

    echo "[setup_dev_env] Loading IC heating actors"
    load_modules "${IC_MODULES[@]}"

    echo "[setup_dev_env] Loading NBI actors"
    load_modules "${NBI_MODULES[@]}"

    echo "[setup_dev_env] Loading additional actors"
    load_modules "${OTHER_MODULES[@]}"
else
    echo "[setup_dev_env] 'module' command not available, skipping module loads"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[setup_dev_env] Creating virtual environment"
    python3 -m venv "${VENV_DIR}"
else
    echo "[setup_dev_env] Virtual environment already exists"
fi

export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"

VENV_PYTHON="${VENV_DIR}/bin/python"
echo "[setup_dev_env] Upgrading pip"
"${VENV_PYTHON}" -m pip install --upgrade pip

echo "[setup_dev_env] Installing project in editable mode with dev extras"
"${VENV_PYTHON}" -m pip install -e .
"${VENV_PYTHON}" -m pip install -e ".[dev]"

cat <<EOF

Development environment is ready.

To use it in the current shell run:
  source ${VENV_DIR}/bin/activate

Common workflow entry points:
  hcd_gui                          # Launch interactive GUI
  hcd_nogui -c data/GRAYSCALE/     # Run full workflow headless
  hcdslice_nogui -c data/GRAYSCALE/  # Run single time-slice headless

EOF

if [[ -n "${ACTOR_FOLDER_ENV}" ]]; then
    cat <<EOF

Local actor folder has been added to PYTHONPATH:
  export PYTHONPATH=${ACTOR_FOLDER}:\$PYTHONPATH

EOF
fi

cat <<EOF

To target another DD release:
  config_hcd_iter_sdcc.sh 4.0.0

EOF
