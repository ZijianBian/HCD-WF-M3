#!/bin/bash
# Post-install test of a NEMO module, called by build_hcd_modules.sh with the module loaded in a clean
# environment (same interface as TORBEAM/test_module.sh):
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with nemo_run_setup below <workdir>, runs the tests listed below with all
# outputs, logs, sandboxes and caches below <workdir>, and appends rc and key results to
# <summary_file>. Returns 0 when every run succeeds and its output checks pass.
#  - CI case: ci-sdcc/st03-run-actor.sh of the run kit (iWrap actor), with ST03_DIR=<workdir>/st03
#  - MUSCLE3 actor: ./run_muscle of the run directory on the default case of input/scenario.yaml (public ITER 130012/5, t = 200 s),
#    output in <workdir>/m3; the output distribution_sources IDS must have a non-empty source array

set -uo pipefail
T_WORK=${1:?usage: test_module.sh <workdir> <summary_file>}
T_SUMMARY=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"
t_init NEMO nemo_run_setup
t_st03 st03 ST03_DIR="$T_WORK/st03"
mkdir -p "$T_WORK/m3"
sed -i -e "s#^output_user_or_path:.*#output_user_or_path: $T_WORK/m3/out#" "$RUN/input/scenario.yaml"
export NEMO_SANDBOX_DIR="$T_WORK/m3/sandbox"
t_cmd muscle3 ./run_muscle
t_entry muscle3 "$T_WORK/m3/out/*/*/*/*" distribution_sources source
t_done
