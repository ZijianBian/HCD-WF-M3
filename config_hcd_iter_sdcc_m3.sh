#!/usr/bin/env bash
# =============================================================================
# config_hcd_iter_sdcc_m3.sh
# 
# HCD-WF environment for DD 4.0.0 using IMAS-Python (IMASPy 2.x)
# 
# UPDATED based on supervisor guidance:
#   - Uses IMAS-Python (IMASPy 2.x) instead of IMAS-AL-Python (HLI)
#   - Uses local iWrap from develop branch (not the module)
#   - Actors must be recompiled with this iWrap version
#
# Reference: /home/ITER/schneim/public/git/torbeam/tests/test_imas/config_sdcc.sh
# =============================================================================

module purge >& /dev/null
set -uo pipefail

# === Module Definitions (DD 4.0.0) ===

# IMAS-Python for DD 4.0.0 (replaces AL-Python and AL-Core)
IMAS_PYTHON_MOD="IMAS-Python/2.0.1-intel-2023b"
IMAS_FORTRAN_MOD="IMAS-AL-Fortran/5.4.0-intel-2023b-DD-4.0.0"
IDSTOOLS_MOD="IDStools/2.3.0-intel-2023b"

# Communication layer
MUSCLE_MOD="MUSCLE3/0.8.0-intel-2023b"

# Auxiliary tools
XMLLIB_MOD="XMLlib/3.3.2-intel-compilers-2023.2.1"
INTERPOS_MOD="INTERPOS/9.2.0-iimkl-2023b"

# Database backend (if needed)
MDSPLUS_MOD="MDSplus/7.132.0-GCCcore-13.2.0"

# Virtual environment name
VENV_DIR="devenv_m3"

echo "=============================================="
echo "Setting up HCD Environment"
echo "  DD 4.0.0 + IMAS-Python (IMASPy 2.x)"
echo "=============================================="
echo ""

# === Load Modules ===
if command -v module >/dev/null 2>&1; then
    echo "[setup] Purging old modules..."
    module purge

    echo "[setup] Loading modules..."
    echo ""
    
    echo "  Loading: ${IMAS_PYTHON_MOD}"
    module load "${IMAS_PYTHON_MOD}"
    
    echo "  Loading: ${IMAS_FORTRAN_MOD}"
    module load "${IMAS_FORTRAN_MOD}"
    
    echo "  Loading: ${IDSTOOLS_MOD}"
    module load "${IDSTOOLS_MOD}"
    
    echo "  Loading: ${MUSCLE_MOD}"
    module load "${MUSCLE_MOD}"
    
    echo "  Loading: ${XMLLIB_MOD}"
    module load "${XMLLIB_MOD}"
    
    echo "  Loading: ${INTERPOS_MOD}"
    module load "${INTERPOS_MOD}"

    echo ""
    echo "[setup] Loaded modules:"
    module list 2>&1 | grep -E "(IMAS|MUSCLE|DD|IDS)" | head -20
else
    echo "[setup] ERROR: 'module' command not found!"
    return 1 2>/dev/null || exit 1
fi

# === Local iWrap from develop branch ===
# NOTE: Do NOT load the iWrap module - use the local version instead
# The official module is not yet compatible with IMAS-Python
echo ""
echo "[setup] Setting up local iWrap (develop branch)..."
export PATH=/home/ITER/schneim/public/git/iwrap/bin:$PATH
export PYTHONPATH=/home/ITER/schneim/public/git/iwrap/python:$PYTHONPATH
echo "  iWrap bin: /home/ITER/schneim/public/git/iwrap/bin"
echo "  iWrap python: /home/ITER/schneim/public/git/iwrap/python"

# === Disable some access layer checks ===
export IMAS_AL_DISABLE_VALIDATE=1  # Mandatory when radial extension is activated
#export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

# === Setup Virtual Environment ===
echo ""
if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[setup] Creating virtual environment: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}" --system-site-packages
else
    echo "[setup] Virtual environment exists: ${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

# === Install Dependencies ===
echo ""
echo "[setup] Upgrading pip..."
pip install --upgrade pip --quiet

if ! python3 -c "import libmuscle" &> /dev/null; then
    echo "[setup] Installing muscle3..."
    pip install muscle3 --quiet
fi

if [[ -f "setup.py" ]] || [[ -f "pyproject.toml" ]]; then
    echo "[setup] Installing hcdworkflow..."
    pip install -e . --quiet
fi

# === Verification ===
echo ""
echo "=============================================="
echo "Verification:"
echo "=============================================="

python3 << 'PYCHECK'
import sys

try:
    import imas
    print(f"[✓] IMAS imported")
    print(f"    File: {imas.__file__}")
    
    # Check for IMASPy 2.x API (ids_defs)
    if hasattr(imas, 'ids_defs'):
        print(f"[✓] imas.ids_defs found (IMASPy 2.x API)")
    elif hasattr(imas, 'imasdef'):
        print(f"[!] imas.imasdef found (HLI/AL-Python API)")
        print(f"    This is the OLD API - you may have loaded IMAS-AL-Python")
        print(f"    Please check module loading")
    else:
        print(f"[?] Unknown IMAS API version")
    
    # Try to check version
    if hasattr(imas, '__version__'):
        print(f"    Version: {imas.__version__}")

except ImportError as e:
    print(f"[✗] Cannot import imas: {e}")
    sys.exit(1)

try:
    import libmuscle
    print(f"[✓] MUSCLE3 imported")
except ImportError as e:
    print(f"[✗] Cannot import libmuscle: {e}")
    sys.exit(1)

# Check iWrap availability
import shutil
iwrap_path = shutil.which('iwrap')
if iwrap_path:
    print(f"[✓] iWrap found: {iwrap_path}")
    if '/home/ITER/schneim/' in iwrap_path:
        print(f"    Using local develop branch (correct!)")
else:
    print(f"[✗] iWrap not found in PATH")
    sys.exit(1)

print("")
print("All checks passed!")
PYCHECK

VERIFY_RESULT=$?

echo ""
if [[ $VERIFY_RESULT -eq 0 ]]; then
    cat <<EOF
==============================================
SETUP COMPLETE!
==============================================

Environment: DD 4.0.0 + IMAS-Python (IMASPy 2.x)
Virtual env: ${VENV_DIR}
iWrap: Local develop branch from /home/ITER/schneim/public/git/iwrap

IMPORTANT: You must recompile your actors with this iWrap version!
  
  # Example for torbeam actor:
  cd /path/to/actor/source
  iwrap generate ...  # (your actor generation command)

The recompiled actors will use IMAS-Python instead of AL-Core.

To activate this environment later:
  source ${VENV_DIR}/bin/activate

EOF
else
    cat <<EOF
==============================================
SETUP FAILED!
==============================================

Please check:
1. Module availability: module avail IMAS-Python
2. Local iWrap path exists: ls /home/ITER/schneim/public/git/iwrap/

EOF
fi