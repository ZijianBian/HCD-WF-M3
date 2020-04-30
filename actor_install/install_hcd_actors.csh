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

set actor_list=(cyrano gray hcd2core-profiles \
  hcd2core-sources iccoup ids-tools lion risk spot stixredist ascot \
  tomcat nemo genray pion)

foreach actor ($actor_list)
  python actor_install.py --skipModules $actor.yml
end

cd ${PWD}
