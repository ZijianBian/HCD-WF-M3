# Start from clean environment
module purge >& /dev/null

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# For actor release procedure
module load sh

# Library to process xml with Python
module load lxml/4.6.2-GCCcore-10.2.0

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
module load WFtools/1.1.2-intel-2020b
module load Waveform-Cooker/1.3.1-GCCcore-10.2.0

# For local re-compilation of actors
module load iWrap
module load XMLlib
module load FRUIT
module load FRUIT_processor
module load INTERPOS
module load PSPLINE
module load NAG/26-intel-2020b
module load netCDF-Fortran/4.5.3-iimpi-2020b
module load CMake/3.18.4-GCCcore-10.2.0
module load Fundamental-Constants
module load `module avail AMNS/*-intel-2020b* -t |tail -n 1 | sed -e 's/[(]default[)]//g'` 

# Workflow tools (local version)
#export PYTHONPATH=/home/ITER/schneim/public/git/wftools/:$PYTHONPATH

# Waveform cooker (local version)
#export PYTHONPATH=/home/ITER/schneim/public/git/waveform-cooker/:$PYTHONPATH

# Avoid doublons in PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"


