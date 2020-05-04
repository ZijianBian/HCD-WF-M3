# Start from clean environment
module purge

# IMAS and FC2K
module load IMAS/3.28.0-4.7.2 FC2K/4.9.0-Java-1.8

# Actor folder
export ACTOR_FOLDER=~/public/PYTHON_ACTORS
mkdir -p $ACTOR_FOLDER
echo "H&CD actors taken from" $ACTOR_FOLDER

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Intel as default compiler
export FCOMPILER=ifort

# For actor release procedure
module load sh/1.12.14-intel-2018a-Python-3.6.4

# Library to process xml with Python
module load lxml/4.2.0-intel-2018a-Python-3.6.4

# Libraries needed for the compilation of the H&CD codes themselves
module load FRUIT/3.4.3-intel-2018a-Ruby-2.5.1
module load FRUIT_processor/3.4.3-intel-2018a-Ruby-2.5.1
module load INTERPOS/9.0.2-intel-2018a
module load XMLlib/3.2.0-intel-2018a
module load PSPLINE/2.0.0-intel-2018a
module load PyAL/1.3.1-intel-2018a-Python-3.6.4
module load NAG/26-intel-2018a

# Add the folder where the generic scripts for H&CD wf are stored to PYTHONPATH
HCD_FOLDER="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=$HCD_FOLDER/tools:$PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"
