#!/bin/bash
# Post-install test of a StixReDist module, called by build_hcd_modules.sh with the module loaded in a clean
# environment (same interface as TORBEAM/test_module.sh):
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with stixredist_run_setup below <workdir>, runs the tests listed below with all
# outputs, logs, sandboxes and caches below <workdir>, and appends rc and key results to
# <summary_file>. Returns 0 when every run succeeds and its output checks pass.
#  - CI case: ci-sdcc/st03-run-actor.sh of the run kit (iWrap actor), with ST03_DIR=<workdir>/st03
#  - MUSCLE3 actor: ./run_muscle of the run directory on the st03 case (ci-sdcc/st03-scenario.yaml),
#    output in <workdir>/m3; the output distributions IDS must have a non-empty distribution array

set -uo pipefail
T_WORK=${1:?usage: test_module.sh <workdir> <summary_file>}
T_SUMMARY=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"
t_init StixReDist stixredist_run_setup
t_st03 st03 ST03_DIR="$T_WORK/st03"
mkdir -p "$T_WORK/m3"
sed -e "s#@CI_IMASDB@#$RUN/ci-sdcc/st03-imasdb#" -e "s#@CI_OUTDB@#$T_WORK/m3/imasdb#" "$RUN/ci-sdcc/st03-scenario.yaml" > "$RUN/input/scenario.yaml"
export MS_TEST_MODE=1 STIXREDIST_SANDBOX_DIR="$T_WORK/m3/sandbox"
t_cmd muscle3 ./run_muscle
t_entry muscle3 "$T_WORK/m3/imasdb/*/*/*/*" distributions distribution
t_done
