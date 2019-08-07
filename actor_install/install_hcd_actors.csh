#!/bin/tcsh

echo ''
echo 'Compiles of actors needed for the HCD workflows (Kepler and Python)'
echo ''

set ACTOR_RELEASE_DIRECTORY=/tmp/${USER}/actor_release/
mkdir -p ${ACTOR_RELEASE_DIRECTORY}

if ( $# > 0 ) then
  if ( "$1" == "-h" ) then
    exit 0
  else
    set ACTOR_RELEASE_DIRECTORY=$1
  endif
endif

set PWD=`pwd`
cp actor_install.py *.yml ${ACTOR_RELEASE_DIRECTORY}
cd ${ACTOR_RELEASE_DIRECTORY}

python actor_install.py --skipModules core_sources_combiner.yml
python actor_install.py --skipModules cyrano.yml
python actor_install.py --skipModules gray.yml
python actor_install.py --skipModules hcd2core-profiles.yml
python actor_install.py --skipModules hcd2core-sources.yml
python actor_install.py --skipModules iccoup.yml
python actor_install.py --skipModules ids-tools.yml
python actor_install.py --skipModules lion.yml
python actor_install.py --skipModules risk.yml
python actor_install.py --skipModules spot.yml
python actor_install.py --skipModules stixredist.yml
python actor_install.py --skipModules ascot.yml
python actor_install.py --skipModules tomcat.yml
python actor_install.py --skipModules nemo.yml
python actor_install.py --skipModules genray.yml

cd ${PWD}
