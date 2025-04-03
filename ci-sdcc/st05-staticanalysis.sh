#!/bin/bash
# Bamboo CI script to test IDS tools on different toolchains
# Execute script from root directory
# Note Disable set -e option when using on local as it will exit the shell on error
if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -u -o pipefail
fi
set -e -u -o pipefail
module load Python

ENVIRONEMNT_NAME=env"$TOOLCHAIN_VERSION"_"$ACCESS_LAYER_VERSION"

python -m venv "$ENVIRONEMNT_NAME"

. "$ENVIRONEMNT_NAME"/bin/activate
# Install and run linters
pip install --upgrade 'black >=24,<25' flake8 pylint ruff

echo "---------------------------------------------------------------------"
echo "executing black"
black --check -l 120 hcdworkflow | tee black_hcdworkflow.log
black --check -l 120 tools | tee black_tools.log
black --check -l 120 gui | tee black_gui.log
black --check -l 120 workflow | tee black_workflow.log
echo "---------------------------------------------------------------------"
echo "executing flake8"
flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow | tee flake8_hcdworkflow.log
flake8 --max-line-length=120 --ignore=E203,W503 tools | tee flake8_tools.log
flake8 --max-line-length=120 --ignore=E203,W503 workflow | tee flake8_workflow.log
flake8 --max-line-length=120 --ignore=E203,W503 gui | tee flake8_gui.log

echo "---------------------------------------------------------------------"
echo "executing pylint"
pylint --max-line-length=120 --disable=E0401 -E --ignore=_version.py ./hcdworkflow/*.py | tee pylint_hcdworkflow.log 
pylint --max-line-length=120 --disable=E0401 -E --ignore=_version.py ./tools/*.py | tee pylint_tools.log
pylint --max-line-length=120 --disable=E0401 -E --ignore=_version.py ./gui/*.py | tee pylint_gui.log
pylint --max-line-length=120 --disable=E0401 -E --ignore=_version.py ./workflow/*.py | tee pylint_workflow.log
echo "---------------------------------------------------------------------"

echo "executing ruff"
ruff check hcdworkflow --select F401,E402 | tee ruff_hcdworkflow.log
ruff check tools --select F401,E402  | tee ruff_tools.log
ruff check gui --select F401,E402  | tee ruff_gui.log
ruff check workflow --select F401,E402  | tee ruff_workflow.log

deactivate
rm -rf "$ENVIRONEMNT_NAME"
echo "Done"