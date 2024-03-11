#!/bin/bash
# Bamboo CI script to create build information for easybuild
# Execute script from root directory

source ./ci-build/st00-header.sh $1 $2

# if successuful create hash and store in actor directory
COMMITHASH=$(git rev-parse HEAD)
VERSION=$(git describe --tags --always)
rm -f ./ci-build/versioninfo.txt
cat >>./ci-build/versioninfo.txt <<EOF
COMMITHASH=$COMMITHASH
MODULE_VERSION=$VERSION
IMAS_VERSION=$IMAS_VERSION
AL_VERSION=$AL_VERSION
TOOLCHAIN_VERSION=$TOOLCHAIN_VERSION
BUILDMODULES=${BUILDMODULES[@]}
RUNMODULES=${RUNMODULES[@]}
EBBUILDMODULES=${EBBUILDMODULES[@]}
EBRUNMODULES=${EBBRUNMODULES[@]}
EOF

set -x
cat ./ci-build/versioninfo.txt
set +x

# Create ci acrtifact
tar -cvzf ci-build.tar.gz ci-build inputs >/dev/null 2>&1

# show contents of artifact
tar -tzvf ci-build.tar.gz

echo "Done"
