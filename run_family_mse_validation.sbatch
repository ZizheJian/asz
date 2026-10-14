#!/bin/bash
#SBATCH --job-name=asz-family-mse-six
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
module load anaconda/2024.02-py311
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONUNBUFFERED=1
python run_family_mse_validation.py --manifest configs/family_mse_validation.json --executables install/bin --output "results/family-mse-six-${SLURM_JOB_ID}"
