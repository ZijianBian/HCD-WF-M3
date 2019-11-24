module purge

# IMAS, Kepler, FC2K
module load IMAS
module load Kepler
module load FC2K/4.6.5-PyAL

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Compile actors without diagnostic information
# (the diag info is not compatible with Python yet, see IMAS-2186)
export DIAG_INFO=-DNO_DIAG_INFO

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

