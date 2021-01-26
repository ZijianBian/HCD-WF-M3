#!/bin/sh
# Set up Python packages for the workflow
set -e

echo Installing dependencies in $PYTHONUSERBASE
$PIP install --user pylint black flake8 anybadge regex
