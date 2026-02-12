#!/bin/bash
# =============================================================================
# HCD-Workflow Benchmark Runner
# =============================================================================
# 
# Two execution modes:
#   direct : Direct MUSCLE3 mode - Driver directly communicates with
#            Fortran actors via MUSCLE3 (e.g. torbeam_m3.exe)
#   hybrid : Hybrid MUSCLE3 mode - Driver communicates with Python iWrap
#            actors via MUSCLE3 (e.g. actor_m3_wrapper.py)
#
# Usage:
#   ./run_benchmark.sh              # Default: direct mode
#   ./run_benchmark.sh direct       # Direct mode (Fortran actors)
#   ./run_benchmark.sh hybrid       # Hybrid mode (Python iWrap actors)
#
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse mode argument
MODE="${1:-direct}"

# Validate mode
if [[ "$MODE" != "direct" && "$MODE" != "hybrid" ]]; then
    echo "=========================================="
    echo "ERROR: Invalid mode '$MODE'"
    echo "=========================================="
    echo ""
    echo "Usage: $0 [direct|hybrid]"
    echo ""
    echo "  direct : Direct MUSCLE3 mode"
    echo "           Driver -> Fortran M3 actors"
    echo ""
    echo "  hybrid : Hybrid MUSCLE3 mode"
    echo "           Driver -> Python iWrap actors"
    echo ""
    exit 1
fi

# Clear MUSCLE environment
unset MUSCLE_CONFIGURATION
unset MUSCLE_INSTANCE

# Configuration based on mode
case "$MODE" in
    "direct")
        TEST_DIR="."
        YMMSL_FILE="test_torbeam_fortran.ymmsl"
        MODE_DESC="Direct MUSCLE3 (Driver -> Fortran torbeam_m3.exe)"
        RUN_PREFIX="run_direct"
        ;;
    "hybrid")
        TEST_DIR="."
        YMMSL_FILE="test_hybrid_hcdwf.ymmsl"
        MODE_DESC="Hybrid MUSCLE3 (Driver -> Python iWrap actors)"
        RUN_PREFIX="run_hybrid"
        ;;
esac

# Check if test directory exists
if [ ! -d "$TEST_DIR" ]; then
    echo "ERROR: Test directory not found: $TEST_DIR"
    exit 1
fi

# Check if YMMSL file exists
YMMSL_PATH="$TEST_DIR/$YMMSL_FILE"
if [ ! -f "$YMMSL_PATH" ]; then
    echo "ERROR: YMMSL file not found: $YMMSL_PATH"
    exit 1
fi

# Create output directory with incrementing number
BASE_DIR="$TEST_DIR/runs"
mkdir -p "$BASE_DIR"

NEXT_NUM=1
while true; do
    DIR_NAME="$BASE_DIR/${RUN_PREFIX}_$(printf "%03d" $NEXT_NUM)"
    if [ ! -d "$DIR_NAME" ]; then
        break
    fi
    NEXT_NUM=$((NEXT_NUM + 1))
done
mkdir -p "$DIR_NAME"

# Print banner
echo "=========================================="
echo "HCD-Workflow Benchmark Runner"
echo "=========================================="
echo "Mode:             $MODE"
echo "Description:      $MODE_DESC"
echo "Test directory:   $TEST_DIR"
echo "YMMSL file:       $YMMSL_FILE"
echo "Output directory: $DIR_NAME"
echo "=========================================="
echo ""

# Record configuration
cat > "$DIR_NAME/run_config.txt" << EOF
Run Configuration
=================
Date:        $(date)
Mode:        $MODE
Description: $MODE_DESC
Test Dir:    $TEST_DIR
YMMSL:       $YMMSL_FILE
Output:      $DIR_NAME
Host:        $(hostname)
User:        $(whoami)
EOF

# Change to test directory and run
cd "$TEST_DIR"

echo "Starting workflow..."
echo ""

# Run muscle_manager
time muscle_manager --start-all "$YMMSL_FILE" || echo "Warning: MUSCLE3 manager exited with an error code."

# Move MUSCLE3 output directory to our run directory
# MUSCLE3 creates a directory like run_<model_name>_<timestamp>
MUSCLE_OUTPUT=$(ls -td run_* 2>/dev/null | head -1)
if [ -n "$MUSCLE_OUTPUT" ] && [ -d "$MUSCLE_OUTPUT" ]; then
    mv "$MUSCLE_OUTPUT" "$DIR_NAME/muscle3_output"
    echo ""
    echo "MUSCLE3 output moved to: $DIR_NAME/muscle3_output"
fi
