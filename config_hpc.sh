
# Location of IMAS actors (pre-compiled)
if [ -z "$KEPLER_DOT" ]
then
    export ACTOR_POOL=$PWD/actor_install/actors
    unset local_kepler
    echo "H&CD actors taken from ~/actor_install/actors"
else
    export local_kepler=`echo $KEPLER_DOT | awk -F "/" '{print $NF}'`
    export ACTOR_POOL=$KEPLER_DOT/kepler/
    echo "Local Kepler" $local_kepler "loaded --> H&CD actors taken from there"
fi

module purge

# IMAS, Kepler, FC2K
module load IMAS
module load Kepler
module load FC2K

# Re-load Kepler if it was loaded already
if [ -z "$local_kepler" ]
    export KEPLER=$ACTOR_POOL # (still needed by IMAS actors themselves)
then
    kepler_load $local_kepler >& /dev/null
fi

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
module load PyAL/1.1.2-intel-2018a-Python-3.6.4
module load NAG/26-intel-2018a

