#!/usr/bin/env bash
# =============================================================================
# run_env_iwrap.sh
# 
# Runtime environment for executing iWrap actors with IMAS-Python (DD 4.0.0)
# 
# This script is called by MUSCLE3 to set up the environment before
# running each actor. 
#
# Usage (called by MUSCLE3 via YMMSL):
#   run_env_iwrap.sh <script.py> [args...]
#
# =============================================================================

# === Clean start ===
module purge >& /dev/null 2>&1

# === Load modules in correct order ===
# Load IMAS-AL-Fortran first (it may pull AL-Core 5.4.2)
module load IMAS-AL-Fortran/5.4.0-intel-2023b-DD-4.0.0 >& /dev/null 2>&1

# Load other required modules
module load XMLlib/3.3.2-intel-compilers-2023.2.1 >& /dev/null 2>&1
module load INTERPOS/9.2.0-iimkl-2023b >& /dev/null 2>&1
module load MUSCLE3/0.8.0-intel-2023b >& /dev/null 2>&1

# Load IMAS-Python LAST - this will reload AL-Core to 5.4.3
module load IMAS-Python/2.0.1-intel-2023b >& /dev/null 2>&1

# === Local iWrap from develop branch ===
export PATH=/home/ITER/schneim/public/git/iwrap/bin:$PATH
export PYTHONPATH=/home/ITER/schneim/public/git/iwrap/python:$PYTHONPATH

# === Disable validation (needed for radial extension) ===
export IMAS_AL_DISABLE_VALIDATE=1

# === Set actor folder ===
export ACTOR_FOLDER=/home/ITER/bianz/public/PYTHON_ACTORS

export PYTHONUNBUFFERED=1

# === Add actor folder to PYTHONPATH ===
export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH
export PYTHONPATH=/home/ITER/bianz/public/git/repository/hcd-wf-sandbox:$PYTHONPATH

# === Remove stack limit to avoid segfaults ===
ulimit -Ss unlimited 2>/dev/null

# === Execute the actual command ===
# All arguments passed to this script are the actual command to run
exec python3 "$@"