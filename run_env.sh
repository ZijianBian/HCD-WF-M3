#!/bin/bash
export PYTHONNOUSERSITE=1

# 1. Load the full Intel environment
source /etc/profile.d/modules.sh
module purge
module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
module load IMAS-AL-Fortran/5.4.0-intel-2023b-DD-3.42.0
module load INTERPOS/9.2.0-iimkl-2023b
module load XMLlib/3.3.2-intel-compilers-2023.2.1
module load TORBEAM/3.8.0-intel-2023b-DD-3.42.0
#module load Waveform-Cooker/1.6.0-GCCcore-13.2.0

# 2. Activate virtual environment
source /home/ITER/bianz/public/git/repository/hcd-wf/devenv_m3/bin/activate

# 3. Path configuration
CURRENT_DIR="/home/ITER/bianz/public/git/repository/hcd-wf"
VENV_LIB="$CURRENT_DIR/devenv_m3/lib/python3.11/site-packages"

# 4. Ensure system MUSCLE3 is in the Python path
export PYTHONPATH="$VENV_LIB:$CURRENT_DIR:$PYTHONPATH"

# 5. Execute
exec "$CURRENT_DIR/devenv_m3/bin/python" "$@"
