#!/bin/bash
# Bamboo CI script to create source distribution and whl package
# Execute script from root directory

# setup environment
# Get toolchain version
source ./ci-build/st00-header.sh $1 $2

# Note Disable set -e option when using on local as it will exit the shell on error
set -e -u -o pipefail

if [ -d "dist" ]; then
    rm -rf "dist"
fi

# Debuggging:
set -x
# create a source distribution
python -m build --sdist
# create wheel compiled version of the package
python -m build --wheel
set +x

echo "Done"
