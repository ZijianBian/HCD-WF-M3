#!/bin/bash
# Post-install test of a SPECE module, called by build_hcd_modules.sh with the module loaded in a clean
# environment (same interface as TORBEAM/test_module.sh):
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with spece_run_setup below <workdir>, runs the tests listed below with all
# outputs, logs, sandboxes and caches below <workdir>, and appends rc and key results to
# <summary_file>. Returns 0 when every run succeeds and its output checks pass.
#  - CI case: ci-sdcc/st03-run-actor.sh of the run kit (iWrap actor run_spece and MUSCLE3 actor on the public ITER case of ci-sdcc/st03-scenario.yaml, t_radiation compared), with CI_WORK_DIR=<workdir>/st03

set -uo pipefail
T_WORK=${1:?usage: test_module.sh <workdir> <summary_file>}
T_SUMMARY=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"
t_init SPECE spece_run_setup
t_st03 st03 CI_WORK_DIR="$T_WORK/st03"
t_done
