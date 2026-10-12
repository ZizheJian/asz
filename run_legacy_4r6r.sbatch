#!/bin/bash
#SBATCH --job-name=asz-4r6r-middle
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=16G
#SBATCH --time=03:00:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
six_job_build=$(mktemp -d /tmp/asz-4r6r-middle.XXXXXX)
g++ -std=c++20 -O3 -march=x86-64-v3 -I c_codes/asz_core c_codes/s2_many_prediction.cpp build/common_zstd_build/lib/libzstd.a -pthread -o "$six_job_build/s2_many_prediction"
g++ -std=c++20 -O3 -march=x86-64-v3 c_codes/s3_conclude_sp_result.cpp -o "$six_job_build/s3_conclude_sp_result"
module load anaconda/2024.02-py311
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MPLCONFIGDIR="$six_job_build/mpl"
python run_legacy_predictor_families.py run --sweep "$six_job_build/s2_many_prediction" --conclude "$six_job_build/s3_conclude_sp_result" --families 1d4r 1d6r --six-grid transition --targets shared1d --datasets isabel cesmt aramco --workers "${SLURM_CPUS_PER_TASK}" --output "results/predictor-family-4r6r-middle-${SLURM_JOB_ID}"
