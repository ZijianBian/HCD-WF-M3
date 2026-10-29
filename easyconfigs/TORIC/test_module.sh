#!/bin/bash
# Post-install test of a TORIC module, called by build_hcd_modules.sh with the module loaded in a clean
# environment (same interface as TORBEAM/test_module.sh):
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with toric_run_setup below <workdir>, runs the tests listed below with all
# outputs, logs, sandboxes and caches below <workdir>, and appends rc and key results to
# <summary_file>. Returns 0 when every run succeeds and its output checks pass.
#  - CI case: ci-sdcc/st03-run-actor.sh of the run kit (iWrap actor run_toric.py and MUSCLE3 actor run_muscle on the public ITER 130012/4 case, results compared), with ST03_DIR=<workdir>/st03

set -uo pipefail
T_WORK=${1:?usage: test_module.sh <workdir> <summary_file>}
T_SUMMARY=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"
t_init TORIC toric_run_setup
t_st03 st03 ST03_DIR="$T_WORK/st03"
t_done
