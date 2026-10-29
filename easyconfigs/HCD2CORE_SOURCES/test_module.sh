#!/bin/bash
# Post-install test of a HCD2CORE_SOURCES module, called by build_hcd_modules.sh with the module loaded
# in a clean environment (same interface as TORBEAM/test_module.sh):
#     test_module.sh <workdir> <summary_file>
# Creates a run directory with hcd2core_sources_run_setup below <workdir>, runs the tests listed below
# with all outputs, logs, sandboxes and caches below <workdir>, and appends rc and key results to
# <summary_file>. Returns 0 when every run succeeds and its output checks pass.
# The repository has no st03 CI case: the documented user sequence is run instead, on the default
# case of input/scenario.yaml (public iter 130012/4, DD3, t = 100 s), output in <workdir>/out:
#  - iWrap actor: python run_hcd2core_sources.py (run_out 26)
#  - MUSCLE3 actor: ./run_muscle (run_out 27)
# Both output core_sources IDSs must have a non-empty source array. HOME points to <workdir>/home
# during the runs, so that the default iWrap sandbox ($HOME/IWRAP_SANDBOX) stays in <workdir>.

set -uo pipefail
T_WORK=${1:?usage: test_module.sh <workdir> <summary_file>}
T_SUMMARY=${2:?usage: test_module.sh <workdir> <summary_file>}
source "$(dirname "${BASH_SOURCE[0]}")/../_lib/test_lib.sh"
t_init HCD2CORE_SOURCES hcd2core_sources_run_setup

scen=$RUN/input/scenario.yaml
mkdir -p "$T_WORK/out" "$T_WORK/home"
sed -i -e "s#^output_user_or_path:.*#output_user_or_path: $T_WORK/out#" "$scen"

sed -i -e 's#^run_out:.*#run_out:             26#' "$scen"
t_cmd iwrap env HOME="$T_WORK/home" python run_hcd2core_sources.py
t_entry iwrap "$T_WORK/out/*/*/130012/26" core_sources source

sed -i -e 's#^run_out:.*#run_out:             27#' "$scen"
t_cmd muscle3 env HOME="$T_WORK/home" ./run_muscle
t_entry muscle3 "$T_WORK/out/*/*/130012/27" core_sources source
t_done
