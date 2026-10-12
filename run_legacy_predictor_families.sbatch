#!/bin/bash
#SBATCH --job-name=asz-family-middle
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
legacy_job_build=$(mktemp -d /tmp/asz-family-middle.XXXXXX)
g++ -std=c++20 -O3 -march=x86-64-v3 -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o "$legacy_job_build/s2_many_prediction"
g++ -std=c++20 -O3 -march=x86-64-v3 c_codes/s3_conclude_sp_result.cpp -o "$legacy_job_build/s3_conclude_sp_result"
module load anaconda/2024.02-py311
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python run_legacy_predictor_families.py run --sweep "$legacy_job_build/s2_many_prediction" --conclude "$legacy_job_build/s3_conclude_sp_result" --workers "${SLURM_CPUS_PER_TASK}" --output "results/predictor-family-legacy-middle-${SLURM_JOB_ID}"
