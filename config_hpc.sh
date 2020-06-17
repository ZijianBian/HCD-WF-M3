# Start from clean environment
module purge

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# For actor release procedure
module load sh/1.12.14-intel-2018a-Python-3.6.4

# Library to process xml with Python
module load lxml/4.2.0-intel-2018a-Python-3.6.4

# Actor folder (to replace some H&CD modules freshly recompiled)
export ACTOR_FOLDER=~/public/PYTHON_ACTORS
mkdir -p $ACTOR_FOLDER

# IMAS and FC2K
module load IMAS FC2K

# Module for all needed HCD or WF actors are loaded
actor_list=(ASCOT SPOT CYRANO FPSIM GENRAY GRAY GRAYSCALE HCD2CORE_PROFILES \
            HCD2CORE_SOURCES LION NBISIM2 NEMO PION RISK StixReDist TOMCAT WFtools)
for actor in ${actor_list[@]}; do
  module load $actor
  export local_${actor}=0
done

# Change local_XXX=1 to replace XXX module by the local one in ~/public/PYTHON_ACTORS
#export local_ASCOT=1

# Add the folder where the generic scripts for H&CD wf are stored to PYTHONPATH
export HCD_FOLDER="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=$HCD_FOLDER:$PYTHONPATH
export PYTHONPATH=$HCD_FOLDER/tools:$PYTHONPATH
export PYTHONPATH=$HCD_FOLDER/interface:$PYTHONPATH
export PYTHONPATH=$HCD_FOLDER/workflow:$PYTHONPATH

# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

# Optionally replace modules by locally compiled versions for H&CD codes and WF tools
if [ $local_ASCOT == 1 ]; then
    echo Warning: BBNBI,ASCOT and AFSI modules replaced by actor from \~/public/PYTHON_ACTORS
    module unload ASCOT
    export PYTHONPATH=$ACTOR_FOLDER/bbnbi:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/ascot4serial:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/ascot4parallel:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/afsi:$PYTHONPATH
fi

if [ $local_SPOT == 1 ]; then
    echo Warning: SPOT module replaced by actor from \~/public/PYTHON_ACTORS
    module unload SPOT
    export PYTHONPATH=$ACTOR_FOLDER/spot:$PYTHONPATH
fi
if [ $local_CYRANO == 1 ]; then
    echo Warning: CYRANO module replaced by actor from \~/public/PYTHON_ACTORS
    module unload CYRANO
    export PYTHONPATH=$ACTOR_FOLDER/Cyrano:$PYTHONPATH
fi
if [ $local_FPSIM == 1 ]; then
    echo Warning: FPSIM \(ICCOUP\) module replaced by actor from \~/public/PYTHON_ACTORS
    module unload FPSIM
    export PYTHONPATH=$ACTOR_FOLDER/iccoup:$PYTHONPATH
fi
if [ $local_GENRAY == 1 ]; then
    echo Warning: GENRAY module replaced by actor from \~/public/PYTHON_ACTORS
    module unload GENRAY
    export PYTHONPATH=$ACTOR_FOLDER/genray:$PYTHONPATH
fi
if [ $local_GRAY == 1 ]; then
    echo Warning: GRAY module replaced by actor from \~/public/PYTHON_ACTORS
    module unload GRAY
    export PYTHONPATH=$ACTOR_FOLDER/gray:$PYTHONPATH
fi
if [ $local_GRAYSCALE == 1 ]; then
    echo Warning: GRAYSCALE module replaced by actor from \~/public/PYTHON_ACTORS
    module unload GRAYSCALE
    export PYTHONPATH=$ACTOR_FOLDER/grayscale:$PYTHONPATH
fi
if [ $local_HCD2CORE_PROFILES == 1 ]; then
    echo Warning: HCD2CORE_PROFILES module replaced by actor from \~/public/PYTHON_ACTORS
    module unload HCD2CORE_PROFILES
    export PYTHONPATH=$ACTOR_FOLDER/hcd2core_profiles:$PYTHONPATH
fi
if [ $local_HCD2CORE_SOURCES == 1 ]; then
    echo Warning: HCD2CORE_SOURCES module replaced by actor from \~/public/PYTHON_ACTORS
    module unload HCD2CORE_SOURCES
    export PYTHONPATH=$ACTOR_FOLDER/hcd2core_sources:$PYTHONPATH
fi
if [ $local_LION == 1 ]; then
    echo Warning: LION module replaced by actor from \~/public/PYTHON_ACTORS
    module unload LION
    export PYTHONPATH=$ACTOR_FOLDER/lion/0:$PYTHONPATH
fi
if [ $local_NBISIM2 == 1 ]; then
    echo Warning: NBISIM2 module replaced by actor from \~/public/PYTHON_ACTORS
    module unload NBISIM2
    export PYTHONPATH=$ACTOR_FOLDER/nbisim2:$PYTHONPATH
fi
if [ $local_NEMO == 1 ]; then
    echo Warning: NEMO module replaced by actor from \~/public/PYTHON_ACTORS
    module unload NEMO
    export PYTHONPATH=$ACTOR_FOLDER/nemo:$PYTHONPATH
fi
if [ $local_PION == 1 ]; then
    echo Warning: PION module replaced by actor from \~/public/PYTHON_ACTORS
    module unload PION
    export PYTHONPATH=$ACTOR_FOLDER/pion:$PYTHONPATH
fi
if [ $local_RISK == 1 ]; then
    echo Warning: RISK module replaced by actor from \~/public/PYTHON_ACTORS
    module unload RISK
    export PYTHONPATH=$ACTOR_FOLDER/:$PYTHONPATH
fi
if [ $local_StixReDist == 1 ]; then
    echo Warning: StixReDist module replaced by actor from \~/public/PYTHON_ACTORS
    module unload StixReDist
    export PYTHONPATH=$ACTOR_FOLDER/StixReDist:$PYTHONPATH
fi
if [ $local_TOMCAT == 1 ]; then
    echo Warning: TOMCAT module replaced by actor from \~/public/PYTHON_ACTORS
    module unload TOMCAT
    export PYTHONPATH=$ACTOR_FOLDER/tomcat:$PYTHONPATH
fi
if [ $local_WFtools == 1 ]; then
    echo Warning: empty and mergers modules replaced by actor from \~/public/PYTHON_ACTORS
    module unload WFtools
    export PYTHONPATH=$ACTOR_FOLDER/empty_core_profiles:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/empty_core_sources:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/empty_distributions:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/empty_distribution_sources:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/empty_waves:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_core_sources:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_distributions:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_distribution_sources:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_waves:$PYTHONPATH
fi

# Avoid doublons in PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"
