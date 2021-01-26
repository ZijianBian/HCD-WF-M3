#!/bin/sh
# Run flake8 code quality for HDC workflow
set -e

# Prepare env
my_dir=$(dirname $0)
. $my_dir/00_setenv_modules.sh
. $my_dir/10_setenv_imas_monorepo.sh
. $my_dir/20_setenv_pure_python.sh
. $my_dir/40_setenv_actors.sh
. $my_dir/50_setenv_workflow.sh
. $my_dir/51_python_deps_workflow.sh

mkdir -p ./flake8
$FLAKE8 --exit-zero --doctests --statistics --count $PYTHON_FILES | tee flake8.txt
PEP8_VIOLATIONS=$(tail flake8.txt -n1)
echo "Flake8 finds $PEP8_VIOLATIONS PEP8 violations"
$ANYBADGE -ou --label=flake8 --value=$PEP8_VIOLATIONS --file=flake8/flake8.svg -c silver

# Your results will be in the ./flake8 artifact
