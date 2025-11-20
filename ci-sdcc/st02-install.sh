#!/bin/bash
# Bamboo CI script to build actor and run standalone program
# Execute script from root directory

source ./ci-sdcc/st00-header.sh $1 $2

# Note Disable set -e option when using on local as it will exit the shell on error
if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -u -o pipefail
fi
module unload Python-bundle-PyPI

#remove previously created environment
VIRTUALENV_DIR=virtualenvdir
if [ -d "$VIRTUALENV_DIR" ]; then
    rm -r "$VIRTUALENV_DIR"
fi

# create virtual env
python3 -m venv "$VIRTUALENV_DIR"

# activate virtual env
source "$VIRTUALENV_DIR"/bin/activate

# install created wheel package
pip install dist/*.whl

# sanity test
python3 -c "from hcdworkflow.workflow_actor import WorkflowActor"


# test workflow
echo "Executing standalone workflow"
#TODO Enable tests once iwrap issue is resolved
# python hcd_nogui -c data/DT_baseline_example || exit 1
# python hcd_nogui -c tests/data/EC_IC_NBI || exit 1
# python hcd_nogui -c tests/data/FOPLA_TEST || exit 1
hcd_nogui -c tests/data/GRAYSCALE >hcd_grayscale.log

echo "Executing single time slice"
#TODO Enable tests once iwrap issue is resolved
# python hcdslice_nogui -c data/DT_baseline_example || exit 1
# python hcdslice_nogui -c tests/data/EC_IC_NBI || exit 1
# python hcdslice_nogui -c tests/data/FOPLA_TEST || exit 1
hcdslice_nogui -c tests/data/GRAYSCALE >hcdslice_grayscale.log
deactivate

echo "Done"
