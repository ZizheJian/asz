#!/bin/bash
#SBATCH --job-name=asz-t-range-lower
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

cd /home/x-zjian1/asz
run_root="/tmp/asz-t-range-lower-${SLURM_JOB_ID}"
cmake -S c_codes -B "${run_root}/build" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/build" --target s1_compress s1_decompress --parallel "${SLURM_CPUS_PER_TASK}"
export ASZ_EXECUTABLE_DIRECTORY="${run_root}/build"
python3 t1_start_compressors.py t_range_lower_extension --skip-build --no-csv
