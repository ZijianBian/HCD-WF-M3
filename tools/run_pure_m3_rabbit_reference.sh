#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 && $# -ne 5 ]]; then
    echo "Usage: $0 OUTPUT_RUN [TBEGIN TEND DT VALIDATION_TIME]" >&2
    exit 2
fi

if [[ ! "$1" =~ ^[0-9]+$ ]]; then
    echo "ERROR: OUTPUT_RUN must be a non-negative integer" >&2
    exit 2
fi

run_out="$1"
if [[ $# -eq 1 ]]; then
    tbegin="100.0"
    tend="100.0"
    dt="2"
    validation_time="100"
    one_time_slice="1"
else
    tbegin="$2"
    tend="$3"
    dt="$4"
    validation_time="$5"
    one_time_slice="0"
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
actor_folder="${ACTOR_FOLDER:-${HOME}/public/PYTHON_ACTORS}"
output_path="${HOME}/public/imasdb/ITER/4/105102/${run_out}"

if [[ -e "$output_path" ]]; then
    echo "ERROR: output run already exists: $output_path" >&2
    exit 3
fi

work_dir="$(mktemp -d "/tmp/hcdwf-rabbit-${run_out}.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
case_dir="$work_dir/case"
ymmsl_file="$work_dir/pure_m3_rabbit_no_fopla.ymmsl"

cp -a "$repo_root/tests/m3_pure_rabbit" "$case_dir"
sed -i -E \
    "s|(<run_out[^>]*>)[^<]+(</run_out>)|\1${run_out}\2|" \
    "$case_dir/input_workflow.xml"
sed -i -E \
    -e "s|(<tbegin[^>]*>)[^<]+(</tbegin>)|\1${tbegin}\2|" \
    -e "s|(<tend[^>]*>)[^<]+(</tend>)|\1${tend}\2|" \
    -e "s|(<dt_required[^>]*>)[^<]+(</dt_required>)|\1${dt}\2|" \
    -e "s|(<one_time_slice[^>]*>)[^<]+(</one_time_slice>)|\1${one_time_slice}\2|" \
    "$case_dir/input_workflow.xml"
sed -i -E \
    "s|(<namelist_path>)[^<]+(</namelist_path>)|\1${case_dir}/NBI/nbi_fp/options.nml\2|" \
    "$case_dir/NBI/nbi_fp/input_rabbit.xml"

reference_root="/home/ITER/bianz/public/git/repository/hcd-wf-sandbox"
reference_actors="/home/ITER/bianz/public/PYTHON_ACTORS"
sed \
    -e "s|${reference_root}/tests/m3_pure_rabbit|${case_dir}|g" \
    -e "s|${reference_root}|${repo_root}|g" \
    -e "s|${reference_actors}|${actor_folder}|g" \
    "$repo_root/pure_m3_rabbit_no_fopla.ymmsl" > "$ymmsl_file"

cd "$repo_root"
source "$repo_root/config_hcd_iter_sdcc.sh"

if [[ "$one_time_slice" == "1" ]]; then
    echo "Rabbit run configuration: run=${run_out}, one slice at t=${tbegin}, validation_time=${validation_time}"
else
    echo "Rabbit run configuration: run=${run_out}, time=[${tbegin}, ${tend}), dt=${dt}, validation_time=${validation_time}"
fi

mkdir -p "$actor_folder/rabbit/logs"
log_file="$actor_folder/rabbit/logs/pure_m3_torbeam_cyrano_rabbit_run${run_out}_$(date +%Y%m%d_%H%M%S).log"
muscle_manager --start-all "$ymmsl_file" 2>&1 | tee "$log_file"

python "$repo_root/tools/validate_dd4_hcd_run.py" \
    --user "${USER:-bianz}" \
    --database ITER \
    --shot 105102 \
    --run "$run_out" \
    --time "$validation_time"

echo "Rabbit reference run passed; log: $log_file"
