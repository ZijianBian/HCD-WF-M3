#!/bin/sh
# Run black code quality for HDC workflow
set -e

# Prepare env
my_dir=$(dirname $0)
. $my_dir/00_setenv_modules.sh
. $my_dir/10_setenv_imas_monorepo.sh
. $my_dir/20_setenv_pure_python.sh
. $my_dir/40_setenv_actors.sh
. $my_dir/50_setenv_workflow.sh
. $my_dir/51_python_deps_workflow.sh

mkdir -p ./black
$BLACK --diff --color $PYTHON_FILES
$BLACK --diff $PYTHON_FILES > black/diff_report.txt

# Your results will be in the ./black artifact
