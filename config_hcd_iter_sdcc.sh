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

# EXTEND PYTHON PATH AND AVOID DOUBLONS
export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"

# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

# To find shell scripts in current local folder
export PATH=$PWD:$PATH

# Avoid doublons in PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"

# Load the default IMAS version, no matter what was loaded through the HCD modules themselves
module load IMAS

# For local re-compilation of actors
module load XMLlib

# IWRAP and INTERPOS to re-compile the actors if necessary
module load iWrap INTERPOS

# For GENRAY
module load netCDF-Fortran/4.5.3-iimpi-2020b

# For PION
module load NAG/26-intel-2020b
 

