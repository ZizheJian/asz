#!/bin/bash
#SBATCH --job-name=asz-coeff-block
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --array=0-5
#SBATCH --output=results/coefficient-blockwise-20261012/slurm-%A_%a.out
#SBATCH --error=results/coefficient-blockwise-20261012/slurm-%A_%a.err

set -euo pipefail
cd /home/x-zjian1/asz
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONUNBUFFERED=1
python3 run_coefficient_blockwise_validation.py --dataset-index "${SLURM_ARRAY_TASK_ID}" --executables build-coefficient-validation --output results/coefficient-blockwise-20261012
