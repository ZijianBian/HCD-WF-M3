#!/bin/sh
# Set up IMAS JINTRAC-like Python environment
export PACKAGE=hdc

export PYTHON_INSTALL_DIR=${PYTHON_INSTALL_DIR:-`pwd`/install}

export PATH=$PYTHON_INSTALL_DIR/bin:${PATH}
export PYTHONPATH=$PYTHON_INSTALL_DIR:${PYTHONPATH}
export PYTHONUSERBASE=$PYTHON_INSTALL_DIR
export PYTHON="python3"
export PIP="$PYTHON -m pip"
export PYLINT="$PYTHON -m pylint"
export ANYBADGE="$PYTHON -m anybadge"
export FLAKE8="$PYTHON -m flake8"
export BLACK="$PYTHON -m black"
export PYTHON_FILES=$(find -name "*.py" -not -path "*/install/*")
