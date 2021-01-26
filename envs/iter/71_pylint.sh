#!/bin/sh
# Run pylint code quality for HDC
set -e

# Prepare env
my_dir=$(dirname $0)
. $my_dir/00_setenv_modules.sh
. $my_dir/10_setenv_imas_monorepo.sh
. $my_dir/20_setenv_pure_python.sh
. $my_dir/40_setenv_actors.sh
. $my_dir/50_setenv_workflow.sh
. $my_dir/51_python_deps_workflow.sh

mkdir -p ./pylint
echo Running Pylint for $PACKAGE
#$PYLINT --rcfile=.pylintrc --output-format=text $PACKAGE | tee ./pylint/pylint.log || pylint-exit $?
$PYLINT --rcfile=.pylintrc --output-format=text $PYTHON_FILES | tee ./pylint/pylint.log || pylint-exit $?
PYLINT_SCORE=$(sed -n 's/^Your code has been rated at \([-0-9.]*\)\/.*/\1/p' ./pylint/pylint.log)
echo "Pylint score is $PYLINT_SCORE"
$ANYBADGE -ou --label=pylint --value=$PYLINT_SCORE --file=pylint/pylint.svg 2=red 4=orange 8=yellow 10=green

# Your results will be in the ./pylint artifact
