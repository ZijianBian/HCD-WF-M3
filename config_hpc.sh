module purge

# IMAS, Kepler, FC2K
module load IMAS
module load Kepler
module load FC2K

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
module load interpos/8.2.1-ifort
module load XMLlib/3.2.0-intel-2018a
module load PSPLINE/20181008-intel-2018a
module load PyAL/1.1.1-intel-2018a-Python-3.6.4
module load NAG/26-intel-2018a

# Location for IMAS actors (pre-compiled)
export ACTOR_POOL=$PWD/actor_install/actors
export KEPLER=$ACTOR_POOL # (still needed by IMAS actors themselves)

