#!/bin/bash
# Bamboo CI script to test IDS tools on different toolchains
# Execute script from root directory
# Note Disable set -e option when using on local as it will exit the shell on error
source /etc/profile.d/modules.sh

if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -e -u -o pipefail
fi
module unload Python-bundle-PyPI
# expand aliases
shopt -s expand_aliases

#print hostname
hostname -f

module load Python

ENVIRONEMNT_NAME=envStaticAnalysis

python -m venv "$ENVIRONEMNT_NAME"

. "$ENVIRONEMNT_NAME"/bin/activate
# Install and run linters (configuration in pyproject.toml)
pip install --upgrade ruff
echo "---------------------------------------------------------------------"
echo "executing ruff check"
ruff check
echo "---------------------------------------------------------------------"
echo "executing ruff format --check"
ruff format --check --diff

deactivate
rm -rf "$ENVIRONEMNT_NAME"
echo "Done"