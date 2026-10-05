#!/bin/bash
#SBATCH --job-name=asz-nyx-log
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

cd /home/x-zjian1/asz
run_root="/tmp/asz-nyx-log-${SLURM_JOB_ID}"
cmake -S c_codes -B "${run_root}/build" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/build" --target s1_compress s1_decompress --parallel 8
export ASZ_EXECUTABLE_DIRECTORY="${run_root}/build"
python3 t1_start_compressors.py nyx_current_log_remaining --skip-build --no-csv
