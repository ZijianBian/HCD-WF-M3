# Start from clean environment
module purge >& /dev/null

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# For actor release procedure
module load sh/1.12.14-intel-2018a-Python-3.6.4

# Library to process xml with Python
module load lxml/4.2.0-intel-2018a-Python-3.6.4

# Actor folder (to replace some H&CD modules freshly recompiled)
export ACTOR_FOLDER=~/public/PYTHON_ACTORS
mkdir -p $ACTOR_FOLDER

# Actor list
actor_list=(ASCOT SPOT CYRANO FPSIM GENRAY GRAY GRAYSCALE HCD2CORE_PROFILES \
            HCD2CORE_SOURCES LION NBISIM NEMO PION RISK TOMCAT StixReDist \
	    WFtools TORBEAM FoPla NERINET)

# Force to use exclusively local actors (1) or not (0)
export all_local=1
if [ $all_local == 1 ]; then
    echo Warning: all actors replaced by local versions from ${ACTOR_FOLDER}/
    for actor in ${actor_list[@]}; do
      export local_${actor}=1
    done
else
  # Module for all needed HCD or WF actors are loaded
  for actor in ${actor_list[@]}; do
    #echo "load" $actor
    module load $actor >& /dev/null
    module unload IMAS >& /dev/null # To deal with actors compiled with different IMAS versions
    export local_${actor}=0
  done
fi

# Change local_XXX=1 to replace XXX module by the local one in ${ACTOR_FOLDER}
#export local_ASCOT=1
#export local_NBISIM=1
#export local_StixReDist=1
#export local_CYRANO=1
#export local_GRAY=1

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
if [ $local_ASCOT == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: BBNBI,ASCOT and AFSI modules replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload ASCOT >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/bbnbi:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/ascot4serial:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/ascot4parallel:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/afsi:$PYTHONPATH
fi

if [ $local_SPOT == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: SPOT module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload SPOT >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/spot:$PYTHONPATH
fi

if [ $local_CYRANO == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: CYRANO module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload CYRANO >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/Cyrano:$PYTHONPATH
fi
if [ $local_FPSIM == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: FPSIM \(ICCOUP\) module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload FPSIM >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/iccoup:$PYTHONPATH
fi
if [ $local_GENRAY == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: GENRAY module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload GENRAY >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/genray:$PYTHONPATH
fi
if [ $local_GRAY == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: GRAY module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload GRAY >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/gray:$PYTHONPATH
fi
if [ $local_GRAYSCALE == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: GRAYSCALE module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload GRAYSCALE >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/grayscale:$PYTHONPATH
fi
if [ $local_HCD2CORE_PROFILES == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: HCD2CORE_PROFILES module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload HCD2CORE_PROFILES >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/hcd2core_profiles:$PYTHONPATH
fi
if [ $local_HCD2CORE_SOURCES == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: HCD2CORE_SOURCES module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload HCD2CORE_SOURCES >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/hcd2core_sources:$PYTHONPATH
fi
if [ $local_LION == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: LION module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload LION >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/lion:$PYTHONPATH
fi
if [ $local_NBISIM == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: NBISIM module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload NBISIM >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/nbisim2:$PYTHONPATH
fi
if [ $local_NEMO == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: NEMO module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload NEMO >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/nemo:$PYTHONPATH
fi
if [ $local_PION == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: PION module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload PION >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/pion:$PYTHONPATH
fi
if [ $local_RISK == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: RISK module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload RISK >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/risk:$PYTHONPATH
fi
if [ $local_StixReDist == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: StixReDist module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload StixReDist >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/StixReDist:$PYTHONPATH
fi
if [ $local_TOMCAT == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: TOMCAT module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload TOMCAT >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/tomcat:$PYTHONPATH
fi
if [ $local_WFtools == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: mergers replaced by actors from ${ACTOR_FOLDER}
    fi
    module unload WFtools >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/merge_core_sources:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_distributions:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_distribution_sources:$PYTHONPATH
    export PYTHONPATH=$ACTOR_FOLDER/merge_waves:$PYTHONPATH
fi
if [ $local_TORBEAM == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: TORBEAM module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload TORBEAM >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/torbeam:$PYTHONPATH
fi
if [ $local_FoPla == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: FoPla module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload FoPla >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/fopla:$PYTHONPATH
fi
if [ $local_NERINET == 1 ] || [ $all_local == 1 ]; then
    if [ $all_local != 1 ]; then
      echo Warning: NERINET module replaced by actor from ${ACTOR_FOLDER}
    fi
    module unload NERINET >& /dev/null
    export PYTHONPATH=$ACTOR_FOLDER/nerinet:$PYTHONPATH
fi

# To find shell scripts in current local folder
export PATH=$PWD:$PATH

# Avoid doublons in PYTHONPATH
export PYTHONPATH="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"

# Load the default IMAS version, no matter what was loaded through the HCD modules themselves
module load IMAS

# For local re-compilation of actors
module load XMLlib

# FC2K, PyAL and INTERPOS to re-compile the actors if necessary
module load FC2K INTERPOS

# Fix when actors compiled with different PyAL version
module unload PyAL >& /dev/null
module load PyAL

# For GENRAY
module load netCDF-Fortran/4.4.4-intel-2018a

# For PION
module load NAG/26-intel-2018a  
 

