# Start from clean environment
module purge >&/dev/null

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Load the default IMAS version
module load IMAS

# Workflow tools needed mostly for the HCD gui
module load WFtools
module load Waveform-Cooker/1.3.3-GCCcore-10.2.0

export ACTOR_FOLDER=~/public/PYTHON_ACTORS