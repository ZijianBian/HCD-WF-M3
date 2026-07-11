#!/bin/bash
# =============================================================================
# HCD-Workflow Runner
# =============================================================================
#
# Three execution modes:
#   legacy  : In-process iwrap, no MUSCLE3 (all actors run inside workflow_driver)
#   hybrid  : MUSCLE3 macro-micro, Python micro (driver ↔ hcd_workflow_m3)
#   pure    : MUSCLE3 macro-micro, Fortran actor direct (driver ↔ *_m3.exe)
#             The maintained baseline omits FoPla.
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
        YMMSL_FILE="${HCD_HYBRID_YMMSL:-hcdwf_hybrid_m3.ymmsl}"
        MODE_DESC="Hybrid MUSCLE3 (driver ↔ hcd_workflow_m3.py)"
        RUN_PREFIX="run_hybrid"
        ;;
    "pure")
        YMMSL_FILE="${HCD_PURE_YMMSL:-hcdwf_pure_m3.ymmsl}"
        MODE_DESC="Pure MUSCLE3 (driver ↔ direct M3 actors; no FoPla)"
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
    # status of tee. Disable errexit only around the command so diagnostics can
    # still be collected below.
    set +e
    time python workflow/workflow_driver.py "$CONFIG_PATH" 0 2>&1 | tee "$DIR_NAME/output.log"
    RUN_STATUS=${PIPESTATUS[0]}
    set -e
else
    # MUSCLE3 may leave useful run diagnostics even on failure. Capture its
    # status, move only diagnostics created by this launch, and propagate the
    # original status.
    MANAGER_STARTED_MARKER="$DIR_NAME/muscle_manager.started"
    touch "$MANAGER_STARTED_MARKER"
    set +e
    time muscle_manager --start-all "$YMMSL_FILE"
    RUN_STATUS=$?
    set -e

    MUSCLE_OUTPUT=$(find . -maxdepth 1 -mindepth 1 -type d -name 'run_*' \
        -newer "$MANAGER_STARTED_MARKER" -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr | head -1 | cut -d' ' -f2-)
    MUSCLE_OUTPUT=${MUSCLE_OUTPUT#./}
    if [ -n "$MUSCLE_OUTPUT" ] && [ -d "$MUSCLE_OUTPUT" ]; then
        mv "$MUSCLE_OUTPUT" "$DIR_NAME/muscle3_output"
        echo ""
        echo "MUSCLE3 output moved to: $DIR_NAME/muscle3_output"
    fi
fi

if [[ "$RUN_STATUS" -ne 0 ]]; then
    echo "ERROR: $MODE workflow exited with status $RUN_STATUS" >&2
    exit "$RUN_STATUS"
fi
