#!/bin/bash -l
#SBATCH -J hcd_eb
# sun: MUSCLE3/0.10.0-intel-2025b SIGILLs on the rigel nodes (Xeon E5-2680 v4)
#SBATCH -p sun
#SBATCH -A iter
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --export=NONE
#
# Slurm wrapper of build_hcd_modules.sh (the method lives there): one (code, flavour) pair per job.
#   sbatch -o <work>/logs/%x_%j.log build_modules.sbatch <path of build_hcd_modules.sh> [VAR=value ...] \
#          [--no-test] [--rebuild] <code> <flavour>
# The VAR=value arguments (HCD_MODULES_WORK, HCD_EC_DIR, EB_PREFIX) are set for build_hcd_modules.sh,
# since the job starts with --export=NONE. Usually submitted by:
#   build_hcd_modules.sh --submit <code|all> [<flavour|all>]
script=${1:?usage: build_modules.sbatch <build_hcd_modules.sh> [VAR=value ...] [options] <code> <flavour>}
shift
vars=()
while [[ $# -gt 0 && $1 == [A-Za-z_]*=* ]]; do vars+=("$1"); shift; done
exec env "${vars[@]}" bash "$script" "$@"
