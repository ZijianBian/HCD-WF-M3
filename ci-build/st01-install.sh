#!/bin/bash
# Bamboo script
# Stage 1 : Pip install

# Set up environment
source ci-build/st00-header.sh $* || exit 1

# Create a virtualized environment for installing hcdworkflow
if [ -d "${PREFIX_DIR}" ];
then
    try rm -r ${PREFIX_DIR}
fi

try mkdir ${PREFIX_DIR}

export PYVERSION=$(python3 -c 'import sys; print("%d.%d"% sys.version_info[0:2])')
echo "PYVERSION :" $PYVERSION
export PYTHONPATH=$(get_abs_filename "./${PREFIX_DIR}")/lib/python${PYVERSION}/site-packages:${PYTHONPATH}
echo "PYTHONPATH :" $PYTHONPATH | grep -i hcdworkflow
export PATH=$(get_abs_filename "./${PREFIX_DIR}")/bin:${PATH}
echo "PATH :" $PATH | grep -i hcdworkflow

echo "Installing HCDWorkflow in the local directory"
try python3 -m pip --disable-pip-version-check install --no-deps . --prefix=${PREFIX_DIR} || exit 1
try python3 -c "from src.workflow_actor import WorkflowActor" || exit 1

COMMITHASH=$(git rev-parse HEAD)
VERSION=$(git describe  --tags --always)
rm -f ./ci-build/versioninfo.txt
cat >> ./ci-build/versioninfo.txt << EOF
COMMITHASH=$COMMITHASH
VERSION=$VERSION
EOF
# Stash
tar -cvzf ${PREFIX_DIR}.tar.gz ./${PREFIX_DIR} ./tests ./ci-build

# Clean up
try rm -r ${PREFIX_DIR}

