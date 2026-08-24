#!/bin/bash
# =============================================================================
# HCD-Workflow Runner
# =============================================================================
#
# Three execution modes:
#   legacy  : In-process iwrap, no MUSCLE3 (all actors run inside workflow_driver)
#   hybrid  : MUSCLE3 macro-micro, Python micro (driver ↔ hcd_workflow_m3)
#   pure    : MUSCLE3 macro-micro, Fortran actor direct (driver ↔ *_m3.exe)
#             Default topology omits FoPla so it works with the standard actor
#             installation. Select test_m3_pure.ymmsl explicitly for FoPla.
#
# Prereq: source config_hcd_iter_sdcc.sh once per shell session.
#
# Usage:
#   ./run.sh                # Default: hybrid
#   ./run.sh legacy
#   ./run.sh hybrid
#   ./run.sh pure
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-hybrid}"

if [[ "$MODE" != "legacy" && "$MODE" != "hybrid" && "$MODE" != "pure" ]]; then
    echo "ERROR: Invalid mode '$MODE'"
    echo "Usage: $0 [legacy|hybrid|pure]"
    exit 1
fi

unset MUSCLE_CONFIGURATION
unset MUSCLE_INSTANCE

case "$MODE" in
    "legacy")
        MODE_DESC="Legacy (no MUSCLE3, all actors in-process via iwrap)"
        RUN_PREFIX="run_legacy"
        CONFIG_PATH="tests/m3_hybrid"
        ;;
    "hybrid")
        YMMSL_FILE="${HCD_HYBRID_YMMSL:-test_hybrid_hcdwf.ymmsl}"
        MODE_DESC="Hybrid MUSCLE3 (driver ↔ hcd_workflow_m3.py)"
        RUN_PREFIX="run_hybrid"
        ;;
    "pure")
        YMMSL_FILE="${HCD_PURE_YMMSL:-pure_m3_no_fopla.ymmsl}"
        MODE_DESC="Pure MUSCLE3 (driver ↔ direct M3 actors; no FoPla by default)"
        RUN_PREFIX="run_pure"
        ;;
esac

if [[ "$MODE" != "legacy" && ! -f "$YMMSL_FILE" ]]; then
    echo "ERROR: YMMSL file not found: $YMMSL_FILE"
    exit 1
fi

BASE_DIR="runs"
mkdir -p "$BASE_DIR"

NEXT_NUM=1
while true; do
    DIR_NAME="$BASE_DIR/${RUN_PREFIX}_$(printf "%03d" $NEXT_NUM)"
    if [ ! -d "$DIR_NAME" ]; then break; fi
    NEXT_NUM=$((NEXT_NUM + 1))
done
mkdir -p "$DIR_NAME"

echo "=========================================="
echo "HCD-Workflow Runner"
echo "=========================================="
echo "Mode:             $MODE"
echo "Description:      $MODE_DESC"
if [[ "$MODE" != "legacy" ]]; then
    echo "YMMSL file:       $YMMSL_FILE"
fi
echo "Output directory: $DIR_NAME"
echo "=========================================="
echo ""

cat > "$DIR_NAME/run_config.txt" << EOF
Run Configuration
=================
Date:        $(date)
Mode:        $MODE
Description: $MODE_DESC
Output:      $DIR_NAME
Host:        $(hostname)
User:        $(whoami)
EOF

if [[ "$MODE" != "legacy" ]]; then
    echo "YMMSL:       $YMMSL_FILE" >> "$DIR_NAME/run_config.txt"
fi

RUN_STATUS=0

if [[ "$MODE" == "legacy" ]]; then
    # Keep the log while retaining the Python process' status rather than the
    # status of tee.  Disable errexit only around the command so diagnostics
    # can still be collected below.
    set +e
    time python workflow/workflow_driver.py "$CONFIG_PATH" 0 2>&1 | tee "$DIR_NAME/output.log"
    RUN_STATUS=${PIPESTATUS[0]}
    set -e
else
    # Point MUSCLE3 at our per-run folder with --run-dir, so it writes logs,
    # metadata and per-instance output there directly instead of creating
    # run_<model>_<timestamp> in the repo root.  --run-dir requires the
    # directory to exist already.  Diagnostics land there even on failure, so
    # capture the status and propagate it after reporting the location.
    MUSCLE_OUTPUT="$DIR_NAME/muscle3_output"
    mkdir -p "$MUSCLE_OUTPUT"
    set +e
    time muscle_manager --run-dir "$MUSCLE_OUTPUT" --start-all "$YMMSL_FILE"
    RUN_STATUS=$?
    set -e

    echo ""
    echo "MUSCLE3 output: $MUSCLE_OUTPUT"
fi

if [[ "$RUN_STATUS" -ne 0 ]]; then
    echo "ERROR: $MODE workflow exited with status $RUN_STATUS" >&2
    exit "$RUN_STATUS"
fi
