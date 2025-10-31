#!/bin/bash
# Bamboo CI script to build and package Sphinx documentation
# Execute this script from the repository root.
source /etc/profile.d/modules.sh

if [[ "$(uname -n)" == *"bamboo"* ]]; then
    set -euo pipefail
fi

# expand aliases
shopt -s expand_aliases

# print hostname
hostname -f

module load Python
module load IMAS-AL-Python
module load Tkinter
module load matplotlib
module unload Python-bundle-PyPI

ENVIRONMENT_NAME=envDocs

python -m venv "$ENVIRONMENT_NAME"

. "$ENVIRONMENT_NAME"/bin/activate

pip install --upgrade pip
pip install -e ".[docs]"

echo "---------------------------------------------------------------------"
echo "Building Sphinx documentation"
pushd docs >/dev/null
make clean
make html
popd >/dev/null

echo "---------------------------------------------------------------------"
echo "Packaging documentation"
ARTIFACT_DIR=docs_artifacts
DOCS_ARCHIVE=hcd-wf-docs.zip
mkdir -p "$ARTIFACT_DIR"
rm -f "$ARTIFACT_DIR/$DOCS_ARCHIVE"
(
    cd docs/build || exit 1
    zip -r "../../$ARTIFACT_DIR/$DOCS_ARCHIVE" html >/dev/null
)
echo "Documentation archive created at $ARTIFACT_DIR/$DOCS_ARCHIVE"
echo "---------------------------------------------------------------------"

deactivate
rm -rf "$ENVIRONMENT_NAME"
echo "Done"
