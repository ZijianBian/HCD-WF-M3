# Start from clean environment
module purge >& /dev/null

# One module to rule them all
module load IMAS

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Library to process xml with Python
module load lxml

# I want to see my log and only my log
export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

# Actor folder (to replace some H&CD modules freshly recompiled)
export ACTOR_FOLDER=~/public/PYTHON_ACTORS
mkdir -p $ACTOR_FOLDER
export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH

# Extend python path and avoid doublons
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"

# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

# To find shell scripts in current local folder
export PATH=$PWD:$PATH

# Load the default IMAS version, no matter what was loaded through the HCD modules themselves
module load IMAS

# Workflow tools needed mostly for the HCD gui
module load Waveform-Cooker

# Avoid doublons in PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"


