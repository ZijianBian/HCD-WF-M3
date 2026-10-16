#!/bin/bash
# Bamboo CI script to create source distribution and whl package
# Execute script from root directory

# setup environment
source ./ci-sdcc/st00-header.sh || exit 1

# Note Disable set -e option when using on local as it will exit the shell on error
if [[ -n "${bamboo_buildKey:-}" ]]; then
    set -e -u -o pipefail
fi
#remove previously created environment
VIRTUALENV_DIR=virtualenvdir
if [ -d "$VIRTUALENV_DIR" ]; then
    rm -r "$VIRTUALENV_DIR"
fi

# create virtual env
python3 -m venv "$VIRTUALENV_DIR"

# activate virtual env
source "$VIRTUALENV_DIR"/bin/activate
pip install --upgrade pip
pip install --upgrade build 
if [ -d "dist" ]; then
    rm -rf "dist"
fi

# Debuggging:
# create a source distribution
python -m build --sdist
# create wheel compiled version of the package
python -m build --wheel
deactivate
echo "Done"
