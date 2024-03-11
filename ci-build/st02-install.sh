#!/bin/bash
# Bamboo CI script to build actor and run standalone program
# Execute script from root directory

source ./ci-build/st00-header.sh $1 $2

# Note Disable set -e option when using on local as it will exit the shell on error
# set -e -u -o pipefail
#remove previously created environment
VIRTUALENV_DIR=virtualenvdir
if [ -d "$VIRTUALENV_DIR" ]; then
    try rm -r "$VIRTUALENV_DIR"
fi

# create virtual env
python3 -m venv "$VIRTUALENV_DIR"

# activate virtual env
source "$VIRTUALENV_DIR"/bin/activate

# install created wheel package
pip install dist/*.whl
set -x
# sanity test
python3 -c "from hcdworkflow.workflow_actor import WorkflowActor"

# test workflow
echo "Executing standalone workflow"
# python hcd_nogui -c data/DT_baseline_example || exit 1
# python hcd_nogui -c tests/data/EC_IC_NBI || exit 1
# python hcd_nogui -c tests/data/FOPLA_TEST || exit 1
hcd_nogui -c tests/data/GRAYSCALE >hcd_grayscale.log

echo "Executing single time slice"
# python hcdslice_nogui -c data/DT_baseline_example || exit 1
# python hcdslice_nogui -c tests/data/EC_IC_NBI || exit 1
# python hcdslice_nogui -c tests/data/FOPLA_TEST || exit 1
hcdslice_nogui -c tests/data/GRAYSCALE >hcdslice_grayscale.log

deactivate
set +x
echo "Done"
