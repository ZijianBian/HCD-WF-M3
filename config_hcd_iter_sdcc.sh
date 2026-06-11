#!/usr/bin/env bash
# ================================================================
# Stable HCD-WF + MUSCLE3 + DD 4.1.0 environment (SDCC)
# ================================================================

# Note: do NOT use set -euo pipefail here — this file is sourced into an
# interactive shell and those flags would leak, causing the terminal to exit
# on any non-zero command return code (including tab completion failures).
_hcd_setup_failed=0

echo "=============================================="
echo "Setting up HCD Environment (DD 4.1.0)"
echo "=============================================="

# ------------------------------------------------
# 1. Clean environment (ONLY ONCE)
# ------------------------------------------------
module purge

# ------------------------------------------------
# 2. IMAS stack — MUST BE FIRST
# ------------------------------------------------
module load IMAS-Python
module load IMAS-Fortran
module load IDStools

# ------------------------------------------------
# 3. MUSCLE3 and core tools
# ------------------------------------------------
module load MUSCLE3
module load XMLlib INTERPOS

# Optional — only if needed
# module load MDSplus

# ------------------------------------------------
# 4. Waveform Cooker (safe)
# ------------------------------------------------
module load Waveform-Cooker/1.6.0-GCCcore-13.2.0

# Optional local override. Leave unset to use the module-provided installation.
if [[ -n "${HCDWF_WAVEFORM_COOKER:-}" ]]; then
    export PYTHONPATH="${HCDWF_WAVEFORM_COOKER}:$PYTHONPATH"
    export EBROOTWAVEFORMMINCOOKER="${HCDWF_WAVEFORM_COOKER}"
fi

# ------------------------------------------------
# 5. Local iWrap (develop branch)
# ------------------------------------------------
if [[ -n "${HCDWF_IWRAP_ROOT:-}" ]]; then
    export PATH="${HCDWF_IWRAP_ROOT}/bin:$PATH"
    export PYTHONPATH="${HCDWF_IWRAP_ROOT}/python:$PYTHONPATH"
fi

# ------------------------------------------------
# 6. IMAS settings
# ------------------------------------------------
export IMAS_AL_DISABLE_VALIDATE=1

# ------------------------------------------------
# 7. Actor and sandbox paths
# ------------------------------------------------
if [[ -z "${HCD_SANDBOX:-}" ]]; then
    HCD_SANDBOX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
export HCD_SANDBOX

export ACTOR_FOLDER="${ACTOR_FOLDER:-${HCD_SANDBOX}/PYTHON_ACTORS}"

export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH
export PYTHONPATH=$HCD_SANDBOX:$PYTHONPATH

# ------------------------------------------------
# 8. System limits and optimizations
#    (previously only in run_env_hybrid.sh)
# ------------------------------------------------
export PYTHONUNBUFFERED=1
ulimit -Ss unlimited 2>/dev/null

# ------------------------------------------------
# 9. Python virtual environment
# ------------------------------------------------
VENV_DIR="devenv"

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR" --system-site-packages
fi

source "$VENV_DIR/bin/activate"

if [[ "${HCDWF_SKIP_PIP_INSTALL:-0}" == "1" ]]; then
    echo "Skipping pip install steps (HCDWF_SKIP_PIP_INSTALL=1)"
else
    pip install --upgrade pip --quiet

    # Install MUSCLE3 if missing
    python3 -c "import libmuscle" 2>/dev/null || pip install muscle3 --quiet

    # Install HCD workflow if in repo
    if [[ -f "setup.py" || -f "pyproject.toml" ]]; then
        pip install -e . --quiet
    fi
fi

# ------------------------------------------------
# 10. Diagnostics
# ------------------------------------------------
echo ""
echo "Loaded IMAS-related modules:"
module list 2>&1 | grep -E "IMAS|DD|AL|IDS"

echo ""
python3 << 'PYCHECK'
import imas
import libmuscle
import shutil

print("IMAS OK")
print("IMAS version:", getattr(imas, "__version__", "unknown"))

if hasattr(imas, "ids_defs"):
    print("IMASPy 2.x API detected (GOOD)")
else:
    print("WARNING: Not IMASPy 2.x")

iwrap = shutil.which("iwrap")
print("iWrap:", iwrap if iwrap else "NOT FOUND")

# Verify actor folder
import os
actor_folder = os.environ.get("ACTOR_FOLDER", "")
if actor_folder and os.path.isdir(actor_folder):
    actors = os.listdir(actor_folder)
    print(f"ACTOR_FOLDER: {actor_folder} ({len(actors)} actors)")
else:
    print("WARNING: ACTOR_FOLDER not set or not found")

print("All checks passed")
PYCHECK

echo ""
echo "=============================================="
echo "SETUP COMPLETE (DD 4.1.0)"
echo "Activate later with:"
echo "  source ${VENV_DIR}/bin/activate"
echo "=============================================="
