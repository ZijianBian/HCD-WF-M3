#!/bin/bash
# Bamboo script
# Stage 0 : load modules

get_abs_filename() 
{
  # $1 : relative filename
  if [ -d "$(dirname "$1")" ]; then
    echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  fi
}

# Start from clean environment
module purge >&/dev/null

# Set up environment for compilation
source /usr/share/Modules/init/sh
module use /work/imas/etc/modules/all

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Load the default IMAS version
module load IMAS

# Workflow tools needed mostly for the HCD gui
module load WFtools
module load Waveform-Cooker/1.3.3-GCCcore-10.2.0

pip install -r requirements.txt 

source "ci-build/common.sh"

export PREFIX_DIR=HCDWorkflow
export ACTOR_FOLDER=/work/imas/opt/bamboo_deploy/PYTHON_ACTORS/
export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH
