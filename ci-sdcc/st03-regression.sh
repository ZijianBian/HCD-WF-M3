#!/bin/bash
# Bamboo CI script to run the regression tests with the actors from st02-build-actors.sh
# Execute script from root directory, after st01-create-distribution.sh
#
#   MODULES   modules used to build and run all actors (required)
#   TESTS     space-separated CASE:IDS,IDS entries, CASE being a folder of tests/data and IDS the
#             IDSs the actors must write, e.g. "GRAYSCALE:waves" (required)
#   ACTORS    see st02-build-actors.sh, only needed when actor_paths.env does not exist yet
#   UPDATE_REFERENCE  set to 1 to write the reference values from this run instead of comparing
#   RTOL      relative tolerance of the value comparison (default: 1e-6)
#
# Each case runs on copies of its configuration writing HDF5 output to ci_regression/<CASE>/{full,slice},
# so runs do not touch the user database and can run in parallel.
# The values of each IDS are compared with tests/reference/<CASE>/dd-<IMAS_VERSION>/<IDS>.json
# when that file exists.

source ./ci-sdcc/st00-header.sh || exit 1

# Note Disable set -e option when using on local as it will exit the shell on error
if [[ -n "${bamboo_buildKey:-}" ]]; then
    set -e -u -o pipefail
fi

if [[ -z "${TESTS:-}" ]]; then
    echo "ERROR: Set TESTS to a space-separated list of CASE:IDS,IDS entries, e.g. GRAYSCALE:waves" >&2
    exit 1
fi

ROOT_DIR=$(pwd)

# Actors built (or found in the cache) by st02
if [[ ! -f actor_paths.env ]]; then
    bash ./ci-sdcc/st02-build-actors.sh || exit 1
fi
source ./actor_paths.env

################################################################################################
#                                   Runtime environment                                        #
################################################################################################
# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited
export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

# Extend PYTHONPATH with the actor folders and avoid duplicates
export PYTHONPATH="$ACTOR_PATHS:${PYTHONPATH:-}"
PYTHONPATH="$(perl -e 'print join(":", grep { length and not $seen{$_}++ } split(/:/, $ENV{PYTHONPATH}))')"
export PYTHONPATH

#remove previously created environment
VIRTUALENV_DIR=virtualenvdir
if [ -d "$VIRTUALENV_DIR" ]; then
    rm -r "$VIRTUALENV_DIR"
fi

# create virtual env
python3 -m venv "$VIRTUALENV_DIR"

# activate virtual env
source "$VIRTUALENV_DIR"/bin/activate

# install created wheel package
pip install dist/*.whl

# sanity test
python3 -c "from hcdworkflow.workflow_actor import WorkflowActor"

################################################################################################
#                                   Regression tests                                           #
################################################################################################
RESULTS_DIR="$ROOT_DIR/ci_regression"
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR"

# Point the output of a configuration copy to a local HDF5 database
set_local_output() {
    python3 - "$1/input_workflow.xml" "$2" <<'EOF'
import re, sys
xml_file, output_path = sys.argv[1], sys.argv[2]
text = open(xml_file).read()
for tag, value in (("output_user_or_path", output_path), ("output_backend", "HDF5")):
    text, count = re.subn(rf"(<{tag}\b[^>]*>)[^<]*(</{tag}>)", rf"\g<1>{value}\g<2>", text)
    if count != 1:
        sys.exit(f"{tag} not found in {xml_file}")
open(xml_file, "w").write(text)
EOF
}

# Run one step, keep its log and report the result
run_step() {
    local name=$1 log=$2
    shift 2
    if "$@" >"$log" 2>&1; then
        echo "  $name: OK"
    else
        echo "  $name: FAILED (see $log)"
        tail -n 20 "$log"
        return 1
    fi
}

FAILED=()
for test in $TESTS; do
    case_name=${test%%:*}
    expected_ids=${test#*:}
    [[ "$expected_ids" == "$test" ]] && expected_ids=""

    if [[ ! -d "tests/data/$case_name" ]]; then
        echo "ERROR: tests/data/$case_name does not exist" >&2
        FAILED+=("$case_name")
        continue
    fi

    echo "> Test $case_name"
    # One configuration copy per run: both create the output entry, so a shared one would be overwritten
    for run in full slice; do
        work="$RESULTS_DIR/$case_name/$run"
        mkdir -p "$work"
        cp -r "tests/data/$case_name/." "$work"
        mkdir -p "$work/imasdb"
        set_local_output "$work" "$work/imasdb" || { FAILED+=("$case_name"); continue 2; }
    done

    work="$RESULTS_DIR/$case_name/full"
    run_step "hcd_nogui" "$work/hcd_nogui.log" hcd_nogui -c "$work" || FAILED+=("$case_name:hcd_nogui")
    if [[ -n "$expected_ids" ]]; then
        check_args=(--reference-dir "$ROOT_DIR/tests/reference/$case_name/dd-${IMAS_VERSION:-unknown}")
        check_args+=(--rtol "${RTOL:-1e-6}")
        [[ "${UPDATE_REFERENCE:-}" =~ ^([Tt]rue|1)$ ]] && check_args+=(--update)
        # shellcheck disable=SC2086
        run_step "output check" "$work/check_output.log" \
            python3 "$ROOT_DIR/ci-sdcc/check_output.py" "${check_args[@]}" "$work" ${expected_ids//,/ } ||
            FAILED+=("$case_name:output")
        cat "$work/check_output.log"
    fi

    # hcdslice_nogui does not write results, only its exit status is checked
    work="$RESULTS_DIR/$case_name/slice"
    run_step "hcdslice_nogui" "$work/hcdslice_nogui.log" hcdslice_nogui -c "$work" ||
        FAILED+=("$case_name:hcdslice_nogui")
done
deactivate

echo "-------------------------------------------------------"
if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo "> Regression tests failed: ${FAILED[*]}"
    exit 1
fi
echo "> All regression tests passed"
echo "> Done"
