#!/bin/bash
#SBATCH --job-name=asz-isabel-plan-transfer
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=13
#SBATCH --time=01:00:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

cd /home/x-zjian1/asz
run_root="/tmp/asz-isabel-plan-transfer-${SLURM_JOB_ID}"
cmake -S c_codes -B "${run_root}/build" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/build" --target s1_compress s1_decompress --parallel "${SLURM_CPUS_PER_TASK}"
export ASZ_EXECUTABLE_DIRECTORY="${run_root}/build"
python3 t1_start_compressors.py isabel_plan_transfer --skip-build --no-csv
python3 analyze_plan_transfer.py results/isabel_plan_transfer.csv --shared-method asz_pf24_plan
