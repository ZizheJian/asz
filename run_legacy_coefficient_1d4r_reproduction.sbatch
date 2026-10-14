#!/bin/bash
#SBATCH --job-name=asz-legacy-1d4r
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:35:00
#SBATCH --array=0-2
#SBATCH --output=results/coefficient-blockwise-legacy-1d4r-20261012/slurm-%A_%a.out
#SBATCH --error=results/coefficient-blockwise-legacy-1d4r-20261012/slurm-%A_%a.err

set -euo pipefail
cd /home/x-zjian1/asz
job_root="/tmp/asz-legacy-45c856e-${SLURM_JOB_ID}"
source_root="${job_root}/source"
build_root="${job_root}/build-main"
mkdir -p "${source_root}" "${build_root}" results/coefficient-blockwise-legacy-1d4r-20261012
git archive 45c856e | tar -x -C "${source_root}"
cp -a /home/x-zjian1/asz/third_party/. "${source_root}/third_party/"
git -C "${source_root}" apply /home/x-zjian1/asz/legacy_coefficient_fixed_grid.patch
cmake -S "${source_root}/c_codes" -B "${build_root}" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${build_root}" --target s1_compress s1_decompress --parallel "${SLURM_CPUS_PER_TASK}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONUNBUFFERED=1
python3 run_legacy_coefficient_1d4r_reproduction.py --dataset-index "${SLURM_ARRAY_TASK_ID}" --source "${source_root}" --executables "${build_root}" --output results/coefficient-blockwise-legacy-1d4r-20261012
