#!/bin/bash
# Bamboo CI script to test IDS tools on different toolchains
# Execute script from root directory
# Note Disable set -e option when using on local as it will exit the shell on error
source /etc/profile.d/modules.sh

if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -u -o pipefail
fi

# expand aliases
shopt -s expand_aliases

#print hostname
hostname -f

module load Python

ENVIRONEMNT_NAME=envStaticAnalysis

python -m venv "$ENVIRONEMNT_NAME"

. "$ENVIRONEMNT_NAME"/bin/activate
# Install and run linters
pip install --upgrade 'black >=24,<25' flake8 pylint ruff
mkdir -p black_logs
mkdir -p flake8_logs
mkdir -p pylint_logs
mkdir -p ruff_logs
echo "---------------------------------------------------------------------"
echo "executing black"
black --check -l 120 hcdworkflow | tee black_logs/hcdworkflow.log
black --check -l 120 tools | tee black_logs/tools.log
black --check -l 120 gui | tee black_logs/gui.log
black --check -l 120 workflow | tee black_logs/workflow.log
echo "---------------------------------------------------------------------"
echo "executing flake8"
flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow | tee flake8_logs/hcdworkflow.log
flake8 --max-line-length=120 --ignore=E203,W503 tools | tee flake8_logs/tools.log
flake8 --max-line-length=120 --ignore=E203,W503 workflow | tee flake8_logs/workflow.log
flake8 --max-line-length=120 --ignore=E203,W503 gui | tee flake8_logs/gui.log

echo "---------------------------------------------------------------------"
echo "executing pylint"
pylint --max-line-length=120 --disable=E0401 -E ./hcdworkflow/*.py | tee pylint_logs/hcdworkflow.log 
pylint --max-line-length=120 --disable=E0401 -E ./tools/*.py | tee pylint_logs/tools.log
pylint --max-line-length=120 --disable=E0401 -E ./gui/*.py | tee pylint_logs/gui.log
pylint --max-line-length=120 --disable=E0401 -E ./workflow/*.py | tee pylint_logs/workflow.log
echo "---------------------------------------------------------------------"

echo "executing ruff"
ruff check hcdworkflow --select F401,E402 | tee ruff_logs/hcdworkflow.log
ruff check tools --select F401,E402  | tee ruff_logs/tools.log
ruff check gui --select F401,E402  | tee ruff_logs/gui.log
ruff check workflow --select F401,E402  | tee ruff_logs/workflow.log

deactivate
rm -rf "$ENVIRONEMNT_NAME"
echo "Done"