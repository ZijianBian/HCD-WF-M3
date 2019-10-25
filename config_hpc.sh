module purge

# IMAS, Kepler, FC2K
module load IMAS
module load Kepler
module load FC2K

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# For Python actors
module load PyUAL

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
module load PyUAL/1.0.2-intel-2018a-Python-3.6.4

# To read Machine Description data from the MD datbase
export MD_ACCESS=no
if [ $MD_ACCESS = "yes" ]; then
    echo "m-machine-description module loaded"
    module use --append m-machine-description/src/main/Environment/HPC/modules
    module load m-machine-description
else
    echo "Warning: m-machine-description module not loaded"
fi

