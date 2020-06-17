#!/bin/tcsh

echo ''
echo 'Compile actors needed for the HCD workflow'
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
  hcd2core-sources iccoup wftools lion nbisim risk spot stixredist ascot \
  tomcat nemo genray pion grayscale)

set actor_list=(nbisim)

foreach actor ($actor_list)
  python actor_install.py $actor.yml
end

cd ${PWD}
