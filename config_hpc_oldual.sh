module purge

# IMAS, Kepler, FC2K
module load IMAS/3.21.0-3.8.11
module load Kepler/2.5p4-2.1.5
module load FC2K/4.4.0

# To read Machine Description data from the MD datbase
export MD_ACCESS=no
if [ $MD_ACCESS = "yes" ]; then
    echo "Load m-machine-description module"
    module use --append m-machine-description/src/main/Environment/HPC/modules
    module load m-machine-description
fi

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Switch from Python 2.7 to Python 3
source switch_python_ITER_HPC.sh

# For Python actors
module load PyUAL/1.0.0-foss-2018a-Python-3.6.4

# For actor release procedure
module load sh/1.12.14-foss-2018a-Python-3.6.4

# Compile actors without diagnostic information
# (the diag info is not compatible with Python for this old version of FC2K)
export DIAG_INFO=-DNO_DIAG_INFO

# Library to process xml with Python
module load lxml/4.2.0-foss-2018a-Python-3.6.4

# Libraries needed for the compilation of the H&CD codes themselves
module load FRUIT/3.4.3-intel-2018a-Ruby-2.5.1
module load FRUIT_processor/3.4.3-intel-2018a-Ruby-2.5.1
module load interpos/8.2.1-ifort
module load XMLlib/3.1.0-intel-2018a
module load PSPLINE/20181008-intel-2018a

